use core::traits::Into;
use core::option::OptionTrait;
use core::result::ResultTrait;
use core::num::traits::Zero;
// use core::array::ArrayTrait;
// use starknet::syscalls::call_contract_syscall;
use starknet::{
    ContractAddress,
    // contract_address_const,
    // get_contract_address,
    get_caller_address,
    // SyscallResultTrait
};
use openzeppelin::token::erc20::interface::{IERC20Dispatcher, IERC20DispatcherTrait};
use snforge_std::{
    declare, 
    ContractClassTrait, 
    DeclareResultTrait,
    start_cheat_caller_address_global,
    start_cheat_block_number,
    Token, TokenImpl, TokenTrait, set_balance
    
};
use super::test_utils::{deploy_registry, pk_u16_span_to_felt252_array_for_hash};
use moosh_id::escrow::Escrow::{
    IEscrowDispatcher,
    IEscrowDispatcherTrait,
};

use moosh_id::keyregistry::FalconPublicKeyRegistry::{
    IFalconPublicKeyRegistryDispatcher,
    IFalconPublicKeyRegistryDispatcherTrait
};
use core::poseidon::poseidon_hash_span;
use moosh_id::addressverifier::FalconSignatureVerifier::{
    IFalconSignatureVerifierDispatcher,
};

use super::inputs::falcon_test_vectors_n1024::{PK_N1024, S1_N1024, MSG_POINT_N1024};

// Mock addresses for testing
const MOCK_PROVIDER_KEY_HASH: felt252 = 0x456;
const MOCK_SERVICE_PERIOD: u64 = 100;
const MOCK_TOTAL_AMOUNT: u128 = 1; // 1 STRK token (reduced for testing)
const INITIAL_BALANCE: u256 = u256 { low: 1000, high: 0 }; // Much larger than MOCK_TOTAL_AMOUNT to avoid overflow

fn to_u256(amount: u128) -> u256 {
    u256 { low: amount.into(), high: 0 }
}

// Helper function to deploy the key registry
fn deploy_key_registry() -> IFalconPublicKeyRegistryDispatcher {
    let contract = declare("FalconPublicKeyRegistry").unwrap().contract_class();
    let constructor_args = array![];
    let (contract_address, _) = contract.deploy(@constructor_args).unwrap();
    IFalconPublicKeyRegistryDispatcher { contract_address }
}

// Helper function to deploy the verifier
fn deploy_verifier(key_registry_addr: ContractAddress) -> IFalconSignatureVerifierDispatcher {
    let contract = declare("FalconSignatureVerifier").unwrap().contract_class();
    let constructor_args = array![key_registry_addr.into()];
    let (contract_address, _) = contract.deploy(@constructor_args).unwrap();
    IFalconSignatureVerifierDispatcher { contract_address }
}

// Helper function to deploy the escrow contract
fn deploy_escrows() -> IEscrowDispatcher {
    // First deploy the key registry and verifier
    let key_registry = deploy_registry();
    
    // Register the test public key
    let pk_span = PK_N1024.span();
    let success = key_registry.register_public_key(pk_span);
    assert(success, 'Registration should succeed');
    
    // Calculate key hash
    let pk_felts = pk_u16_span_to_felt252_array_for_hash(pk_span);
    let key_hash = poseidon_hash_span(pk_felts.span());
    
    // Deploy the verifier with the key registry
    let verifier = deploy_verifier(key_registry.contract_address);
    
    // Get STRK token address
    let strk_addr: ContractAddress = Token::STRK.contract_address();
    
    // Prepare constructor args for escrow
    let constructor_args = array![
        key_hash.into(),
        MOCK_TOTAL_AMOUNT.into(),
        MOCK_SERVICE_PERIOD.into(),
        verifier.contract_address.into(),
        strk_addr.into()
    ];
    
    // Declare the contract
    let contract = declare("Escrow").unwrap().contract_class();
    
    // Now deploy the escrow contract
    let (contract_address, _) = contract.deploy(@constructor_args).unwrap();
    
    IEscrowDispatcher { contract_address }
}

#[derive(Drop)]
struct EscrowStateChecks {
    is_deposited: bool,
    is_completed: bool,
    is_claimed: bool,
    is_disputed: bool,
    skip_client_check: bool,
}

impl EscrowStateChecksDefault of Default<EscrowStateChecks> {
    fn default() -> EscrowStateChecks {
        EscrowStateChecks {
            is_deposited: false,
            is_completed: false,
            is_claimed: false,
            is_disputed: false,
            skip_client_check: false,
        }
    }
}

fn setup_test_environment() -> (ContractAddress, ContractAddress) {
    let user_address: ContractAddress = 0x123.try_into().unwrap();
    let strk_addr: ContractAddress = Token::STRK.contract_address();
    
    // Set initial balance using the constant
    set_balance(user_address, INITIAL_BALANCE, Token::STRK);
    start_cheat_caller_address_global(caller_address: user_address);
    
    (user_address, strk_addr)
}

fn assert_token_balance(token: IERC20Dispatcher, account: ContractAddress, expected_balance: u256) {
    let balance = token.balance_of(account);
    assert(balance == expected_balance, 'Incorrect token balance');
}

fn assert_escrow_state(escrow: IEscrowDispatcher, expected_state: EscrowStateChecks) {
    let details = escrow.get_escrow_details();
    
    // Check deposit state
    assert(details.is_deposited == expected_state.is_deposited, 'Wrong deposit state');
    assert(details.is_completed == expected_state.is_completed, 'Wrong completion state');
    assert(details.is_claimed == expected_state.is_claimed, 'Wrong claim state');
    assert(details.is_disputed == expected_state.is_disputed, 'Wrong dispute state');
    
    // Check key parameters
    assert(details.total_amount == MOCK_TOTAL_AMOUNT, 'Wrong total amount');
    assert(details.service_period_blocks == MOCK_SERVICE_PERIOD, 'Wrong service period');
    
    // Verify client address
    if !expected_state.skip_client_check {
        assert(details.client == get_caller_address(), 'Wrong client address');
    }
}

fn setup_escrow_with_deposit() -> (IEscrowDispatcher, IERC20Dispatcher, ContractAddress) {
    let (user_address, strk_addr) = setup_test_environment();
    let escrow = deploy_escrows();
    assert(!escrow.contract_address.is_zero(), 'Contract not deployed');
    
    let strk = IERC20Dispatcher { contract_address: strk_addr };
    
    // Verify initial state
    assert_escrow_state(escrow, EscrowStateChecksDefault::default());
    
    // Check initial balances
    let zero_balance = u256 { low: 0, high: 0 };
    assert_token_balance(strk, user_address, INITIAL_BALANCE);
    assert_token_balance(strk, escrow.contract_address, zero_balance);
    
    // Approve and verify allowance
    let mock_amount_u256 = to_u256(MOCK_TOTAL_AMOUNT);
    let success = strk.approve(escrow.contract_address, mock_amount_u256);
    assert(success, 'Approval failed');
    let allowance = escrow.get_client_allowance();
    assert(allowance == mock_amount_u256, 'Wrong allowance amount');
    
    // Perform deposit
    let success = escrow.deposit();
    assert(success, 'Deposit failed');
    
    // Verify post-deposit state
    assert_escrow_state(
        escrow,
        EscrowStateChecks {
            is_deposited: true,
            is_completed: false,
            is_claimed: false,
            is_disputed: false,
            skip_client_check: false,
        }
    );
    
    // Verify post-deposit balances
    let mock_amount_u256 = to_u256(MOCK_TOTAL_AMOUNT);
    let remaining_balance = INITIAL_BALANCE - mock_amount_u256;
    assert_token_balance(strk, user_address, remaining_balance);
    assert_token_balance(strk, escrow.contract_address, mock_amount_u256);
    
    (escrow, strk, user_address)
}

#[test]
fn test_deploy_escrow() {
    let escrow = deploy_escrows();
    
    // Basic deployment checks
    let details = escrow.get_escrow_details();
    assert(details.provider.is_zero(), 'Provider should be zero');
    assert(!details.is_deposited, 'Should start undeposited');
    assert(!details.is_completed, 'Should start incomplete');
    assert(!details.is_claimed, 'Should start unclaimed');
    assert(!details.is_disputed, 'Should start undisputed');
}

#[should_panic]
#[test]
fn test_prevent_double_deposit() {
    let (escrow, _strk, _user_address) = setup_escrow_with_deposit();
    
    // Verify first deposit succeeded
    let details = escrow.get_escrow_details();
    assert(details.is_deposited, 'First deposit should succeed');
    assert(details.service_start_block > 0, 'Start block should be set');
    
    // Try to deposit again - should panic due to 'Already deposited' assert
    escrow.deposit();
}

#[test]
fn test_successful_claim() {
    let (escrow, strk, user_address) = setup_escrow_with_deposit();
    
    // Create signature data from test vectors
    let s1_coeffs = S1_N1024.span();
    let msg_point = MSG_POINT_N1024.span();
    
    // Warp to after service period
    let service_period = MOCK_SERVICE_PERIOD;
    start_cheat_block_number(escrow.contract_address, service_period + 10000000);
    
    // Claim the escrow with spans
    let success = escrow.claim(s1_coeffs, msg_point);
    assert(success, 'Claim failed');
    
    // Verify escrow state after claim
    assert_escrow_state(
        escrow,
        EscrowStateChecks {
            is_deposited: true,
            is_completed: true,
            is_claimed: true,
            is_disputed: false,
            skip_client_check: false,
        }
    );
    
    // Verify final balances
    let zero_balance = u256 { low: 0, high: 0 };
    assert_token_balance(strk, escrow.contract_address, zero_balance);
    
    // Get the provider address from the escrow details
    let details = escrow.get_escrow_details();
    assert(!details.provider.is_zero(), 'Provider should be set');
    // Provider's final balance should be their initial balance if they were also the original client
    // or their starting balance + MOCK_TOTAL_AMOUNT if they are a distinct entity.
    // In this test, provider is the original caller (user_address).
    assert_token_balance(strk, details.provider, INITIAL_BALANCE); 
    
    // Check remaining client balance (user_address who is also the provider here)
    // This assertion is effectively the same as the one above for details.provider
    assert_token_balance(strk, user_address, INITIAL_BALANCE);
}

#[test]
fn test_dispute_before_start() {
    let (escrow, strk, user_address) = setup_escrow_with_deposit();
    
    // Get the start block
    let details = escrow.get_escrow_details();
    let start_block = details.service_start_block;
    
    // Try to dispute before service starts
    start_cheat_block_number(escrow.contract_address, start_block + 1);
    let success = escrow.dispute();
    assert(success, 'Dispute failed');
    
    // Check final state
    assert_escrow_state(
        escrow,
        EscrowStateChecks {
            is_deposited: true,
            is_completed: true,
            is_claimed: false,
            is_disputed: true,
            skip_client_check: false,
        }
    );
    
    // Since dispute is before start, all funds should return to client
    let zero_balance = u256 { low: 0, high: 0 };
    assert_token_balance(strk, escrow.contract_address, zero_balance);
    assert_token_balance(strk, user_address, INITIAL_BALANCE);
}

#[test]
fn test_dispute_during_service() {
    let (escrow, strk, user_address) = setup_escrow_with_deposit();
    
    let details = escrow.get_escrow_details();
    
    // Calculate midpoint of service period
    let start_block = details.service_start_block;
    let period = details.service_period_blocks;
    let mid_point = start_block + (period / 2);
    
    // Dispute halfway through service
    start_cheat_block_number(escrow.contract_address, mid_point);
    let success = escrow.dispute();
    assert(success, 'Dispute failed');
    
    // Check final state
    assert_escrow_state(
        escrow,
        EscrowStateChecks {
            is_deposited: true,
            is_completed: true,
            is_claimed: false,
            is_disputed: true,
            skip_client_check: false,
        }
    );
    
    // Verify proportional fund distribution
    // At midpoint, funds should be split roughly equally
    let zero_balance = u256 { low: 0, high: 0 };
    let half_amount = u256 { low: MOCK_TOTAL_AMOUNT / 2, high: 0 };
    let expected_client_balance = u256 { 
        low: MOCK_TOTAL_AMOUNT + half_amount.low, 
        high: 0 
    };
    
    assert_token_balance(strk, escrow.contract_address, zero_balance);
    assert_token_balance(strk, user_address, expected_client_balance);
    
    // If provider is set, they should have received their share
    let details = escrow.get_escrow_details();
    if !details.provider.is_zero() {
        assert_token_balance(strk, details.provider, half_amount);
    }
}

#[test]
fn test_dispute_after_service() {
    let (escrow, strk, user_address) = setup_escrow_with_deposit();
    
    let details = escrow.get_escrow_details();
    
    // Calculate end of service period plus some blocks
    let start_block = details.service_start_block;
    let period = details.service_period_blocks;
    let after_end = start_block + period + 10;
    
    // Dispute after service period
    start_cheat_block_number(escrow.contract_address, after_end);
    let success = escrow.dispute();
    assert(success, 'Dispute failed');
    
    // Check final state
    assert_escrow_state(
        escrow,
        EscrowStateChecks {
            is_deposited: true,
            is_completed: true,
            is_claimed: false,
            is_disputed: true,
            skip_client_check: false,
        }
    );
    
    // After full service period, all funds should go to provider if set
    let zero_balance = u256 { low: 0, high: 0 };
    let mock_amount_u256 = to_u256(MOCK_TOTAL_AMOUNT);
    assert_token_balance(strk, escrow.contract_address, zero_balance);
    
    // Get the provider address and check balances
    let details = escrow.get_escrow_details();
    if !details.provider.is_zero() {
        assert_token_balance(strk, details.provider, mock_amount_u256);
        let remaining_balance = INITIAL_BALANCE - mock_amount_u256;
        assert_token_balance(strk, user_address, remaining_balance);
    } else {
        // If no provider set, funds return to client
        assert_token_balance(strk, user_address, INITIAL_BALANCE);
    }
}

#[test]
fn test_get_caller() {
    // Set up user address and STRK balance
    let user_address: ContractAddress = 0x123.try_into().unwrap();
    set_balance(user_address, 1_000_000_000_000_000, Token::STRK);
    start_cheat_caller_address_global(caller_address: user_address);
    
    // Deploy escrow with real verifier
    let escrow = deploy_escrows();
    assert(!escrow.contract_address.is_zero(), 'Contract not deployed');

    // Get escrow details
    let details = escrow.get_escrow_details();
    
    // The caller address should match the client address in the escrow
    assert(get_caller_address() == details.client, 'Caller should be client');
}
