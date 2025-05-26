#[starknet::contract]
pub mod Escrow {
    use core::traits::Into;
    use core::traits::TryInto;
    use core::num::traits::Zero;
    use core::array::Span;
    use starknet::{
        ContractAddress,
        get_contract_address,
        get_caller_address,
    };
    use starknet::event::EventEmitter;

    // Import storage traits
    use starknet::storage::{StoragePointerReadAccess, StoragePointerWriteAccess};
    
    // Import OpenZeppelin ERC20 interface
    use openzeppelin::token::erc20::interface::{IERC20Dispatcher, IERC20DispatcherTrait};
    
    // Import verifier interface
    use moosh_id::addressverifier::FalconSignatureVerifier::{
        IFalconSignatureVerifierDispatcher,
        IFalconSignatureVerifierDispatcherTrait,
    };

    #[storage]
    struct Storage {
        // Core escrow data
        provider_key_hash: felt252,
        total_amount: u128,  // Changed from felt252 to u128
        service_period_blocks: u64,  // Duration of service in blocks
        service_start_block: u64,    // When service starts
        is_completed: bool,
        is_claimed: bool,
        is_disputed: bool,
        is_deposited: bool,         // New field to track if deposit has been made
        
        // Contract participants
        client: ContractAddress,
        provider: ContractAddress,

        // Verifier contract
        verifier: ContractAddress,

        // STRK token contract
        strk_token: ContractAddress,
    }

    #[event]
    #[derive(Drop, starknet::Event)]
    enum Event {
        EscrowCreated: EscrowCreated,
        EscrowDeposited: EscrowDeposited,
        EscrowClaimed: EscrowClaimed,
        EscrowDisputed: EscrowDisputed,
    }

    #[derive(Drop, starknet::Event)]
    struct EscrowCreated {
        client: ContractAddress,
        provider_key_hash: felt252,
        total_amount: u128,
        service_period_blocks: u64
    }

    #[derive(Drop, starknet::Event)]
    struct EscrowDeposited {
        client: ContractAddress,
        amount: u128
    }

    #[derive(Drop, starknet::Event)]
    struct EscrowClaimed {
        provider: ContractAddress,
        amount: u128
    }

    #[derive(Drop, starknet::Event)]
    struct EscrowDisputed {
        client: ContractAddress,
        provider_key_hash: felt252,
        blocks_served: u64,
        provider_amount: u128,
        client_refund: u128
    }

    // Struct to return escrow details
    #[derive(Drop, Serde)]
    pub struct EscrowDetails {
        pub provider_key_hash: felt252,
        pub total_amount: u128,
        pub service_period_blocks: u64,
        pub service_start_block: u64,
        pub is_completed: bool,
        pub is_claimed: bool,
        pub is_disputed: bool,
        pub is_deposited: bool,
        pub client: ContractAddress,
        pub provider: ContractAddress
    }

    #[constructor]
    fn constructor(
        ref self: ContractState,
        provider_key_hash: felt252,
        total_amount: u128,
        service_period_blocks: u64,
        verifier: ContractAddress,
        strk_token: ContractAddress,
        client_address: ContractAddress,
        provider_address: ContractAddress
    ) {
        // Set the escrow parameters
        assert(provider_key_hash != 0, 'Provider addr must be non-zero');
        assert(!client_address.is_zero(), 'Client addr must be non-zero');
        assert(!provider_address.is_zero(), 'Provider addr must be non-zero');
        
        self.provider_key_hash.write(provider_key_hash);
        self.total_amount.write(total_amount);
        self.service_period_blocks.write(service_period_blocks);
        self.verifier.write(verifier);
        self.strk_token.write(strk_token);
        
        // Set the client and provider addresses from parameters
        self.client.write(client_address);
        self.provider.write(provider_address);
        
        // Initialize state
        self.is_completed.write(false);
        self.is_claimed.write(false);
        self.is_disputed.write(false);
        self.is_deposited.write(false);

        // Emit creation event
        self.emit(Event::EscrowCreated(
            EscrowCreated {
                client: client_address,
                provider_key_hash,
                total_amount,
                service_period_blocks
            }
        ));
    }

    #[starknet::interface]
    pub trait IEscrow<TContractState> {
        fn get_escrow_details(self: @TContractState) -> EscrowDetails;
        fn deposit(ref self: TContractState) -> bool;
        fn claim(ref self: TContractState, s1_coeffs: Span<u16>, msg_point: Span<u16>) -> bool;
        fn dispute(ref self: TContractState) -> bool;
        fn get_client_allowance(self: @TContractState) -> u256;
    }

    #[generate_trait]
    impl InternalFunctions of InternalFunctionsTrait {
        fn assert_only_client(self: @ContractState) {
            let caller = get_caller_address();
            let client = self.client.read();
            assert(caller == client, 'Only client can call');
        }

        fn calculate_proportional_amount(
            total_amount: u128,
            total_blocks: u64,
            blocks_served: u64
        ) -> u128 {
            // Convert to u128 for calculation
            let blocks_served_u128: u128 = blocks_served.into();
            let total_blocks_u128: u128 = total_blocks.into();
            
            // Calculate proportional amount using integer division
            let result = (total_amount * blocks_served_u128) / total_blocks_u128;
            
            // Ensure we don't exceed total amount
            if result > total_amount {
                total_amount
            } else {
                result
            }
        }

        fn to_u256(amount: u128) -> u256 {
            u256 { low: amount.into(), high: 0 }
        }

        fn from_u256(amount: u256) -> u128 {
            amount.low.into()
        }

        fn safe_transfer(
            self: @ContractState,
            token: IERC20Dispatcher,
            recipient: ContractAddress,
            amount: u128
        ) -> bool {
            // Convert to u256 for token operations
            let amount_u256 = Self::to_u256(amount);
            
            // Check contract has sufficient balance
            let contract_balance = token.balance_of(get_contract_address());
            assert(contract_balance >= amount_u256, 'Insufficient contract balance');
            
            // Perform transfer
            token.transfer(recipient, amount_u256)
        }

        fn validate_balance_for_operation(
            self: @ContractState,
            required_amount: u128
        ) -> bool {
            let strk = IERC20Dispatcher { contract_address: self.strk_token.read() };
            let contract_balance = strk.balance_of(get_contract_address());
            let required_u256 = Self::to_u256(required_amount);
            contract_balance >= required_u256
        }

        fn get_service_status(self: @ContractState) -> u8 {
            let current_block = starknet::get_block_number();
            let start_block = self.service_start_block.read();
            let period = self.service_period_blocks.read();
            
            if !self.is_deposited.read() {
                0 // NotStarted
            } else if current_block <= start_block {
                1 // Pending
            } else if current_block < start_block + period {
                2 // Active
            } else {
                3 // Completed
            }
        }
    }

    #[abi(embed_v0)]
    impl EscrowImpl of IEscrow<ContractState> {
        fn get_escrow_details(self: @ContractState) -> EscrowDetails {
            EscrowDetails {
                provider_key_hash: self.provider_key_hash.read(),
                total_amount: self.total_amount.read(),
                service_period_blocks: self.service_period_blocks.read(),
                service_start_block: self.service_start_block.read(),
                is_completed: self.is_completed.read(),
                is_claimed: self.is_claimed.read(),
                is_disputed: self.is_disputed.read(),
                is_deposited: self.is_deposited.read(),
                client: self.client.read(),
                provider: self.provider.read()
            }
        }

        fn deposit(ref self: ContractState) -> bool {
            // Only client can deposit
            InternalFunctions::assert_only_client(@self);
            
            // Check if already deposited
            assert(!self.is_deposited.read(), 'Already deposited');
            assert(!self.is_completed.read(), 'Already completed');
            
            // Get the deposit amount
            let total_amount = self.total_amount.read();
            
            // Get contract addresses
            let this_contract = get_contract_address();
            let strk_addr = self.strk_token.read();
            let strk = IERC20Dispatcher { contract_address: strk_addr };
            let client = self.client.read();
            let caller = get_caller_address();
            
            // Debug assertions
            assert(caller == client, 'Caller not client');
            let zero_address: ContractAddress = 0.try_into().unwrap();
            assert(strk_addr != zero_address, 'Invalid token address');
            assert(this_contract != zero_address, 'Invalid escrow address');

            // Convert amount to u256 for token operations
            let amount_u256 = InternalFunctions::to_u256(total_amount);

            // Check client has sufficient balance
            let client_balance = strk.balance_of(client);
            assert(client_balance >= amount_u256, 'Insufficient balance');

            // Check allowance is sufficient
            let allowance = strk.allowance(client, this_contract);
            assert(allowance >= amount_u256, 'Insufficient allowance');
            
            // Debug: Store pre-transfer allowance and verify it matches
            let pre_transfer_allowance = strk.allowance(client, this_contract);
            assert(pre_transfer_allowance == allowance, 'Allowance changed unexpectedly');
            assert(pre_transfer_allowance >= amount_u256, 'Pre-transfer not allowed');
            
            // Transfer STRK tokens from client to contract
            let transfer_success = strk.transfer_from(client, this_contract, amount_u256);
            assert(transfer_success, 'Transfer failed');
            
            // Debug: Verify allowance was consumed
            let post_transfer_allowance = strk.allowance(client, this_contract);
            assert(post_transfer_allowance == pre_transfer_allowance - amount_u256, 'Allowance not properly consumed');
            
            // Set the service start block after deposit
            let current_block = starknet::get_block_number();
            self.service_start_block.write(current_block);
            
            // Mark as deposited
            self.is_deposited.write(true);
            
            // Emit deposit event
            self.emit(Event::EscrowDeposited(
                EscrowDeposited {
                    client: client,
                    amount: total_amount
                }
            ));
            
            true
        }

        fn claim(
            ref self: ContractState,
            s1_coeffs: Span<u16>,
            msg_point: Span<u16>
        ) -> bool {
            // Check if deposit has been made
            assert(self.is_deposited.read(), 'Not deposited');
            
            // Check if already claimed or disputed
            assert(!self.is_claimed.read(), 'Already claimed');
            assert(!self.is_disputed.read(), 'Contract disputed');
            
            // Check service status
            let status = InternalFunctions::get_service_status(@self);
            assert(status == 3, 'Service period not complete');
            
            // Get the key hash and verifier
            let key_hash = self.provider_key_hash.read();
            let verifier = IFalconSignatureVerifierDispatcher { 
                contract_address: self.verifier.read() 
            };
            
            // Could try a pre-committed msg_point with signatures from both keys to 'activate' the agreement if the upstream lib became less 'steps' that it could be run twice
            // TODO: Try ^ with 512 keys in case they are less steps to verify?
            // Verify the signature
            let is_valid = verifier.verify_signature_for_key_hash(
                key_hash,
                s1_coeffs,
                msg_point // Should be pre-determined?
            );
            assert(is_valid, 'Invalid signature');
            
            // Set provider address and mark as claimed
            let caller = get_caller_address();
            self.provider.write(caller);
            self.is_claimed.write(true);
            self.is_completed.write(true);
            
            // Transfer tokens to provider
            let total_amount = self.total_amount.read();
            let strk = IERC20Dispatcher { contract_address: self.strk_token.read() };
            
            // Validate and transfer
            assert(
                InternalFunctions::validate_balance_for_operation(@self, total_amount),
                'Insufficient balance for claim'
            );
            InternalFunctions::safe_transfer(@self, strk, caller, total_amount);
            
            // Emit claim event
            self.emit(Event::EscrowClaimed(
                EscrowClaimed {
                    provider: caller,
                    amount: total_amount
                }
            ));
            
            true
        }

        fn dispute(ref self: ContractState) -> bool {
            // Check if deposit has been made
            assert(self.is_deposited.read(), 'Not deposited');
            
            // Only client can dispute
            InternalFunctions::assert_only_client(@self);
            
            // Check if already claimed or disputed
            assert(!self.is_claimed.read(), 'Already claimed');
            assert(!self.is_disputed.read(), 'Already disputed');
            
            // Get current status
            let status = InternalFunctions::get_service_status(@self);
            let current_block = starknet::get_block_number();
            let start_block = self.service_start_block.read();
            let total_period = self.service_period_blocks.read();
            
            // If not started or pending, return all funds to client
            if status <= 1 {
                let client = self.client.read();
                let total_amount = self.total_amount.read();
                let strk = IERC20Dispatcher { contract_address: self.strk_token.read() };
                
                // Validate and transfer
                assert(
                    InternalFunctions::validate_balance_for_operation(@self, total_amount),
                    'Insufficient balance for refund'
                );
                InternalFunctions::safe_transfer(@self, strk, client, total_amount);
                
                // Emit dispute event
                self.emit(Event::EscrowDisputed(
                    EscrowDisputed {
                        client,
                        provider_key_hash: self.provider_key_hash.read(),
                        blocks_served: 0,
                        provider_amount: 0,
                        client_refund: total_amount
                    }
                ));
                
                // Mark as disputed and completed
                self.is_disputed.write(true);
                self.is_completed.write(true);
                
                return true;
            }
            
            // Calculate blocks served (capped at total period)
            let blocks_served = if status == 3 {
                total_period
            } else {
                current_block - start_block
            };
            
            // Calculate amounts
            let total_amount = self.total_amount.read();
            let provider_amount = InternalFunctions::calculate_proportional_amount(
                total_amount, total_period, blocks_served
            );
            let client_refund = total_amount - provider_amount;
            
            // Get addresses and create token dispatcher
            let client = self.client.read();
            let provider = self.provider.read();
            let strk = IERC20Dispatcher { contract_address: self.strk_token.read() };
            
            // Validate total balance
            assert(
                InternalFunctions::validate_balance_for_operation(@self, total_amount),
                'Insufficient balance to dispute'
            );
            
            // Transfer to provider if applicable
            if provider_amount > 0 && !provider.is_zero() {
                InternalFunctions::safe_transfer(@self, strk, provider, provider_amount);
            }
            
            // Transfer remaining to client
            if client_refund > 0 {
                InternalFunctions::safe_transfer(@self, strk, client, client_refund);
            }
            
            // Mark as disputed and completed
            self.is_disputed.write(true);
            self.is_completed.write(true);
            
            // Emit dispute event
            self.emit(Event::EscrowDisputed(
                EscrowDisputed {
                    client,
                    provider_key_hash: self.provider_key_hash.read(),
                    blocks_served,
                    provider_amount,
                    client_refund
                }
            ));
            
            true
        }

        fn get_client_allowance(self: @ContractState) -> u256 {
            // Get the client address
            let client = self.client.read();
            
            // Get this contract's address
            let this_contract = get_contract_address();
            
            // Create STRK token dispatcher
            let strk_addr = self.strk_token.read();
            let strk = IERC20Dispatcher { contract_address: strk_addr };
            
            // Return the allowance
            strk.allowance(client, this_contract)
        }
    }
} 