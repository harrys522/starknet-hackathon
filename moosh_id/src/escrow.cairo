#[starknet::contract]
pub mod Escrow {
    use core::traits::Into;
    use core::traits::TryInto;
    use core::zeroable;
    use core::num::traits::Zero;
    use core::array::Span;
    use starknet::{
        ContractAddress,
        get_contract_address,
        get_caller_address,
    };

    // Import storage traits
    use starknet::storage::{StoragePointerReadAccess, StoragePointerWriteAccess};
    
    // Import OpenZeppelin ERC20 interface
    use openzeppelin::token::erc20::interface::{IERC20Dispatcher, IERC20DispatcherTrait};
    
    // Import verifier interface
    use moosh_id::addressverifier::FalconSignatureVerifier::{
        IFalconSignatureVerifierDispatcher,
        IFalconSignatureVerifierDispatcherTrait,
    };

    // STRK token address
    use snforge_std::{
        Token,
        TokenTrait
    };

    #[storage]
    struct Storage {
        // Core escrow data
        provider_key_hash: felt252,
        total_amount: u256,
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
        total_amount: u256,
        service_period_blocks: u64
    }

    #[derive(Drop, starknet::Event)]
    struct EscrowDeposited {
        client: ContractAddress,
        amount: u256
    }

    #[derive(Drop, starknet::Event)]
    struct EscrowClaimed {
        provider: ContractAddress,
        amount: u256
    }

    #[derive(Drop, starknet::Event)]
    struct EscrowDisputed {
        client: ContractAddress,
        provider_key_hash: felt252,
        blocks_served: u64,
        provider_amount: u256,
        client_refund: u256
    }

    // Struct to return escrow details
    #[derive(Drop, Serde)]
    pub struct EscrowDetails {
        pub provider_key_hash: felt252,
        pub total_amount: u256,
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
        total_amount: u256,
        service_period_blocks: u64,
        verifier: ContractAddress
    ) {
        // Set the escrow parameters
        self.provider_key_hash.write(provider_key_hash);
        self.total_amount.write(total_amount);
        self.service_period_blocks.write(service_period_blocks);
        self.verifier.write(verifier);
        
        // Set the client address
        let caller = get_caller_address();
        self.client.write(caller);
        
        // Initialize state
        self.is_completed.write(false);
        self.is_claimed.write(false);
        self.is_disputed.write(false);
        self.is_deposited.write(false);

        // Emit creation event
        self.emit(Event::EscrowCreated(
            EscrowCreated {
                client: caller,
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
            total_amount: u256,
            total_blocks: u64,
            blocks_served: u64
        ) -> u256 {
            // Calculate amount based on blocks served
            let blocks_served_u256: u256 = blocks_served.into();
            let total_blocks_u256: u256 = total_blocks.into();
            
            // Use integer division to calculate proportional amount
            // amount = total_amount * blocks_served / total_blocks
            (total_amount * blocks_served_u256) / total_blocks_u256
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
            
            // Transfer STRK tokens from client to contract
            let this_contract = get_contract_address();
            let strk_addr: ContractAddress = Token::STRK.contract_address();
            let strk = IERC20Dispatcher { contract_address: strk_addr };

            // This line casuses the error. Might be because of the allowance.
            strk.transfer_from(self.client.read(), this_contract, total_amount);
            
            // Set the service start block after deposit
            let current_block = starknet::get_block_number();
            self.service_start_block.write(current_block);
            
            // Mark as deposited
            self.is_deposited.write(true);
            
            // Emit deposit event
            self.emit(Event::EscrowDeposited(
                EscrowDeposited {
                    client: self.client.read(),
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

            // Check if service period is complete
            let current_block = starknet::get_block_number();
            let start_block = self.service_start_block.read();
            let period = self.service_period_blocks.read();
            assert(current_block >= start_block + period, 'Service period not complete');

            // Get the key hash and verifier
            let key_hash = self.provider_key_hash.read();
            let verifier_address = self.verifier.read();
            
            // Create verifier dispatcher
            let verifier = IFalconSignatureVerifierDispatcher { 
                contract_address: verifier_address 
            };

            // Verify the signature
            let is_valid = verifier.verify_signature_for_key_hash(
                key_hash,
                s1_coeffs,
                msg_point
            );

            assert(is_valid, 'Invalid signature');

            // Mark as claimed
            self.is_claimed.write(true);
            self.is_completed.write(true);
            
            // Set provider address
            let caller = get_caller_address();
            self.provider.write(caller);

            // Transfer STRK tokens to provider
            let total_amount = self.total_amount.read();
            let strk_addr: ContractAddress = Token::STRK.contract_address();
            let strk = IERC20Dispatcher { contract_address: strk_addr };
            strk.transfer(caller, total_amount);

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
            
            // Calculate blocks served
            let current_block = starknet::get_block_number();
            let start_block = self.service_start_block.read();
            let total_period = self.service_period_blocks.read();
            
            // If dispute is before start, no payment is made
            if current_block <= start_block {
                let client = self.client.read();
                let total_amount = self.total_amount.read();
                
                // Return all funds to client
                let strk_addr: ContractAddress = Token::STRK.contract_address();
                let strk = IERC20Dispatcher { contract_address: strk_addr };
                strk.transfer(client, total_amount);
                
                // Emit dispute event
                self.emit(Event::EscrowDisputed(
                    EscrowDisputed {
                        client,
                        provider_key_hash: self.provider_key_hash.read(),
                        blocks_served: 0,
                        provider_amount: 0.into(),
                        client_refund: total_amount
                    }
                ));
                
                return true;
            }
            
            // Calculate actual blocks served (cap at total period)
            let blocks_served = if current_block - start_block > total_period {
                total_period
            } else {
                current_block - start_block
            };
            
            // Calculate proportional amounts
            let total_amount = self.total_amount.read();
            let provider_amount = InternalFunctions::calculate_proportional_amount(
                total_amount, total_period, blocks_served
            );
            let client_refund = total_amount - provider_amount;
            
            // Get addresses
            let client = self.client.read();
            let provider_key_hash = self.provider_key_hash.read();
            
            // Transfer tokens
            let strk_addr: ContractAddress = Token::STRK.contract_address();
            let strk = IERC20Dispatcher { contract_address: strk_addr };
            
            // Send proportional amount to provider if they served any blocks
            if provider_amount > 0.into() {
                let provider = self.provider.read();
                if !provider.is_zero() {
                    strk.transfer(provider, provider_amount);
                }
            }
            
            // Return remaining funds to client
            if client_refund > 0.into() {
                strk.transfer(client, client_refund);
            }
            
            // Mark as disputed
            self.is_disputed.write(true);
            self.is_completed.write(true);
            
            // Emit dispute event
            self.emit(Event::EscrowDisputed(
                EscrowDisputed {
                    client,
                    provider_key_hash,
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
            let strk_addr: ContractAddress = Token::STRK.contract_address();
            let strk = IERC20Dispatcher { contract_address: strk_addr };
            
            // Return the allowance
            strk.allowance(client, this_contract)
        }
    }
} 