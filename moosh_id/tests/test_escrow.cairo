use core::traits::Into;
use core::option::OptionTrait;
use core::result::ResultTrait;
use core::num::traits::Zero;
use core::byte_array::{ByteArray, ByteArrayTrait};
use core::array::ArrayTrait;
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
    // Token, TokenImpl, TokenTrait, set_balance
    
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
const MOCK_TOTAL_AMOUNT: u128 = 1000000000000000000;  // Increased to 1e18 (1 full token)
const INITIAL_BALANCE: u256 = u256 { low: 1000000000000000000000, high: 0 }; // Increased to 1000e18
const ERC20_RECIPIENT_INITIAL_SUPPLY: felt252 = 0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef;

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

// Helper function to deploy a new ESC token for testing
fn deploy_esc_token(recipient: ContractAddress, initial_supply: u256) -> IERC20Dispatcher {
    let contract = declare("ESCToken").unwrap().contract_class();
    let constructor_args = array![
        initial_supply.low.into(),
        initial_supply.high.into(),
        recipient.into(),
    ];
    let (contract_address, _) = contract.deploy(@constructor_args).unwrap();
    IERC20Dispatcher { contract_address }
}

// Helper function to deploy the escrow contract
fn deploy_escrows(strk_token_dispatcher: IERC20Dispatcher) -> IEscrowDispatcher {
    let key_registry = deploy_registry();
    let pk_span = PK_N1024.span();
    key_registry.register_public_key(pk_span);
    let pk_felts = pk_u16_span_to_felt252_array_for_hash(pk_span);
    let key_hash = poseidon_hash_span(pk_felts.span());
    let verifier = deploy_verifier(key_registry.contract_address);
    
    // Use the address of the ERC20 token we deployed and passed in
    let strk_addr_from_dispatcher = strk_token_dispatcher.contract_address;
    
    let constructor_args = array![
        key_hash.into(),
        MOCK_TOTAL_AMOUNT.into(),
        MOCK_SERVICE_PERIOD.into(),
        verifier.contract_address.into(),
        strk_addr_from_dispatcher.into() // Use our deployed token's address
    ];
    
    let contract = declare("Escrow").unwrap().contract_class();
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

fn setup_test_environment() -> (ContractAddress, IERC20Dispatcher) {
    let user_address: ContractAddress = 0x123.try_into().unwrap();
    let esc_token_dispatcher = deploy_esc_token(user_address, INITIAL_BALANCE);
    start_cheat_caller_address_global(caller_address: user_address);
    (user_address, esc_token_dispatcher)
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
    // Fresh setup for each test
    let (user_address, token) = setup_test_environment();
    let escrow = deploy_escrows(token);
    
    // Debug: Verify clean initial state
    let initial_allowance = token.allowance(user_address, escrow.contract_address);
    assert(initial_allowance == u256 { low: 0, high: 0 }, 'Setup: unexpected allowance');
    
    let initial_balance = token.balance_of(user_address);
    assert(initial_balance == INITIAL_BALANCE, 'Setup: wrong initial balance');
    
    // Set caller and approve
    start_cheat_caller_address_global(caller_address: user_address);
    let amount_u256 = to_u256(MOCK_TOTAL_AMOUNT);
    let success = token.approve(escrow.contract_address, amount_u256);
    assert(success, 'Setup: approval failed');
    
    // Verify approval
    let post_approve_allowance = token.allowance(user_address, escrow.contract_address);
    assert(post_approve_allowance == amount_u256, 'Setup: allowance not set');
    
    // Do deposit
    let success_deposit = escrow.deposit();
    assert(success_deposit, 'Setup: deposit failed');
    
    // Verify deposit consumed allowance
    let final_allowance = token.allowance(user_address, escrow.contract_address);
    assert(final_allowance == u256 { low: 0, high: 0 }, 'Setup: allowance not consumed');
    
    (escrow, token, user_address)
}

// Add this helper function for token approvals
fn approve_tokens(token: IERC20Dispatcher, owner: ContractAddress, spender: ContractAddress, amount: u128) {
    let amount_u256 = to_u256(amount);
    let success = token.approve(spender, amount_u256);
    assert(success, 'Approval failed');
    let allowance = token.allowance(owner, spender);
    assert(allowance == amount_u256, 'Wrong allowance amount');
}

#[test]
fn test_deploy_escrow() {
    // This test will now need to correctly initialize strk_token_dispatcher for deploy_escrows
    let (_user_address, strk_token_dispatcher) = setup_test_environment(); // Prefix user_address with _
    let escrow = deploy_escrows(strk_token_dispatcher);
    
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
    let (escrow, token, user_address) = setup_escrow_with_deposit();
    
    // Create signature data from test vectors
    let s1_coeffs = S1_N1024.span();
    let msg_point = MSG_POINT_N1024.span();
    
    // Set the caller as the provider (who will claim)
    let provider_address = user_address;  // For test simplicity, using same address
    start_cheat_caller_address_global(caller_address: provider_address);
    
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
    assert_token_balance(token, escrow.contract_address, zero_balance);
    assert_token_balance(token, provider_address, INITIAL_BALANCE);
}

#[test]
fn test_dispute_before_start() {
    let (escrow, token, user_address) = setup_escrow_with_deposit();
    
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
    assert_token_balance(token, escrow.contract_address, zero_balance);
    assert_token_balance(token, user_address, INITIAL_BALANCE);
}

#[test]
fn test_dispute_during_service() {
    let (escrow, token, user_address) = setup_escrow_with_deposit();
    
    let details = escrow.get_escrow_details();
    
    // Calculate midpoint of service period
    let start_block = details.service_start_block;
    let period = details.service_period_blocks;
    let mid_point = start_block + (period / 2);
    
    // Set back to client for dispute
    start_cheat_caller_address_global(caller_address: user_address);
    
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
    let zero_balance = u256 { low: 0, high: 0 };
    let half_amount = MOCK_TOTAL_AMOUNT / 2;
    let expected_client_balance = to_u256(INITIAL_BALANCE.low - half_amount);
    
    assert_token_balance(token, escrow.contract_address, zero_balance);
    assert_token_balance(token, user_address, expected_client_balance);
    
    // If provider is set, they should have received their share
    let details = escrow.get_escrow_details();
    if !details.provider.is_zero() {
        assert_token_balance(token, details.provider, to_u256(half_amount));
    }
}

#[test]
fn test_dispute_after_service() {
    let (escrow, token, user_address) = setup_escrow_with_deposit();
    
    let details = escrow.get_escrow_details();
    
    // Calculate end of service period plus some blocks
    let start_block = details.service_start_block;
    let period = details.service_period_blocks;
    let after_end = start_block + period + 10;
    
    // Set back to client for dispute
    start_cheat_caller_address_global(caller_address: user_address);
    
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
    assert_token_balance(token, escrow.contract_address, zero_balance);
    
    // Get the provider address and check balances
    let details = escrow.get_escrow_details();
    if !details.provider.is_zero() {
        assert_token_balance(token, details.provider, to_u256(MOCK_TOTAL_AMOUNT));
        let remaining_balance = INITIAL_BALANCE.low - MOCK_TOTAL_AMOUNT;
        assert_token_balance(token, user_address, to_u256(remaining_balance));
    } else {
        // If no provider set, funds return to client
        assert_token_balance(token, user_address, INITIAL_BALANCE);
    }
}

#[test]
fn test_get_caller() {
    let (user_address, strk_token_dispatcher) = setup_test_environment();
    let escrow = deploy_escrows(strk_token_dispatcher);
    
    // Get escrow details
    let details = escrow.get_escrow_details();
    
    // The caller address should match the client address in the escrow
    assert(get_caller_address() == details.client, 'Caller should be client');
}

#[test]
fn test_token_approval_and_deposit_with_debug() {
    // Setup basic environment
    let (user_address, token) = setup_test_environment();
    let escrow = deploy_escrows(token);
    
    // Debug: Check if there are any existing allowances
    let initial_allowance = token.allowance(user_address, escrow.contract_address);
    assert(initial_allowance == u256 { low: 0, high: 0 }, 'Unexpected initial allowance');
    
    // Debug: Check initial balance
    let initial_balance = token.balance_of(user_address);
    assert(initial_balance == INITIAL_BALANCE, 'Wrong initial balance');
    
    // Set caller and approve
    start_cheat_caller_address_global(caller_address: user_address);
    let amount_u256 = to_u256(MOCK_TOTAL_AMOUNT);
    let success = token.approve(escrow.contract_address, amount_u256);
    assert(success, 'Approval failed');
    
    // Debug: Verify allowance right after approval
    let post_approve_allowance = token.allowance(user_address, escrow.contract_address);
    assert(post_approve_allowance == amount_u256, 'Allowance not set');
    
    // Debug: Check caller right before deposit
    let current_caller = get_caller_address();
    assert(current_caller == user_address, 'Wrong caller pre-deposit');
    
    // Try deposit
    let success_deposit = escrow.deposit();
    assert(success_deposit, 'Deposit failed');
    
    // Debug: Check final allowance
    let final_allowance = token.allowance(user_address, escrow.contract_address);
    assert(final_allowance == u256 { low: 0, high: 0 }, 'Allowance not consumed');
}

#[test]
fn test_claim_after_deposit() {
    // First do deposit
    let (user_address, token) = setup_test_environment();
    let escrow = deploy_escrows(token);
    
    // Approve and deposit
    let amount_u256 = to_u256(MOCK_TOTAL_AMOUNT);
    let success = token.approve(escrow.contract_address, amount_u256);
    assert(success, 'Approval failed');
    let success_deposit = escrow.deposit();
    assert(success_deposit, 'Deposit failed');
    
    // Create signature data
    let s1_coeffs = S1_N1024.span();
    let msg_point = MSG_POINT_N1024.span();
    
    // Warp to after service period
    start_cheat_block_number(escrow.contract_address, MOCK_SERVICE_PERIOD + 10000000);
    
    // Try to claim
    let success_claim = escrow.claim(s1_coeffs, msg_point);
    assert(success_claim, 'Claim failed');
    
    // Verify final state
    let details = escrow.get_escrow_details();
    assert(details.is_claimed, 'Should be claimed');
    assert(!details.is_disputed, 'Should not be disputed');
    
    // Verify final balances
    let zero_balance = u256 { low: 0, high: 0 };
    assert_token_balance(token, escrow.contract_address, zero_balance);
    
    // Provider should have received the funds
    let provider = details.provider;
    assert(!provider.is_zero(), 'Provider should be set');
    assert_token_balance(token, provider, to_u256(MOCK_TOTAL_AMOUNT));
}

#[test]
fn test_dispute_after_deposit() {
    // First do deposit
    let (user_address, token) = setup_test_environment();
    let escrow = deploy_escrows(token);
    
    // Approve and deposit
    let amount_u256 = to_u256(MOCK_TOTAL_AMOUNT);
    let success = token.approve(escrow.contract_address, amount_u256);
    assert(success, 'Approval failed');
    let success_deposit = escrow.deposit();
    assert(success_deposit, 'Deposit failed');
    
    // Get initial state
    let details = escrow.get_escrow_details();
    let start_block = details.service_start_block;
    
    // Try to dispute before service starts
    start_cheat_block_number(escrow.contract_address, start_block + 1);
    let success_dispute = escrow.dispute();
    assert(success_dispute, 'Dispute failed');
    
    // Verify final state
    let final_details = escrow.get_escrow_details();
    assert(final_details.is_disputed, 'Should be disputed');
    assert(!final_details.is_claimed, 'Should not be claimed');
    
    // All funds should return to client
    let zero_balance = u256 { low: 0, high: 0 };
    assert_token_balance(token, escrow.contract_address, zero_balance);
    assert_token_balance(token, user_address, INITIAL_BALANCE);
}

#[test]
fn test_deploy_esc_token() {
    // Setup recipient address
    let recipient: ContractAddress = ERC20_RECIPIENT_INITIAL_SUPPLY.try_into().unwrap();
    
    // Deploy token
    let token = deploy_esc_token(recipient, INITIAL_BALANCE);
    
    // Verify total supply
    let total_supply = token.total_supply();
    assert(total_supply == INITIAL_BALANCE, 'Wrong total supply');
    
    // Check initial balance was minted to recipient
    let recipient_balance = token.balance_of(recipient);
    assert(recipient_balance == INITIAL_BALANCE, 'Initial balance not minted');
    assert(recipient_balance == total_supply, 'Supply mismatch');
    
    // Verify zero balance for other addresses
    let other_address: ContractAddress = 123.try_into().unwrap();
    let other_balance = token.balance_of(other_address);
    assert(other_balance == u256 { low: 0, high: 0 }, 'Other balance should be 0');
}

#[test]
fn test_token_approval() {
    // Setup
    let (user_address, token) = setup_test_environment();
    let spender: ContractAddress = 0x123.try_into().unwrap();
    
    // Ensure we're the token owner
    start_cheat_caller_address_global(caller_address: user_address);
    
    // Verify initial state
    let initial_balance = token.balance_of(user_address);
    assert(initial_balance == INITIAL_BALANCE, 'Wrong initial balance');
    
    let initial_allowance = token.allowance(user_address, spender);
    assert(initial_allowance == u256 { low: 0, high: 0 }, 'Initial allowance not zero');
    
    // Do approval
    let amount = to_u256(MOCK_TOTAL_AMOUNT);
    let success = token.approve(spender, amount);
    assert(success, 'Approval failed');
    
    // Check allowance
    let final_allowance = token.allowance(user_address, spender);
    assert(final_allowance == amount, 'Allowance not set correctly');
    
    // Verify balance unchanged
    let final_balance = token.balance_of(user_address);
    assert(final_balance == INITIAL_BALANCE, 'Balance changed after approve');
}

fn print_token_state(token: IERC20Dispatcher, owner: ContractAddress, spender: ContractAddress) {
    let balance = token.balance_of(owner);
    let allowance = token.allowance(owner, spender);
    let total_supply = token.total_supply();
    
    // Print using assert messages since we don't have println
    assert(balance == balance, 'Balance: {balance}');
    assert(allowance == allowance, 'Allowance: {allowance}');
    assert(total_supply == total_supply, 'Supply: {total_supply}');
}

#[test]
fn test_allowance_consumption() {
    // Setup basic environment
    let (user_address, token) = setup_test_environment();
    let escrow = deploy_escrows(token);
    
    // Set caller and approve
    start_cheat_caller_address_global(caller_address: user_address);
    let amount_u256 = to_u256(MOCK_TOTAL_AMOUNT);
    
    // Debug: Print initial state
    print_token_state(token, user_address, escrow.contract_address);
    
    // Initial allowance should be zero
    let initial_allowance = token.allowance(user_address, escrow.contract_address);
    assert(initial_allowance == u256 { low: 0, high: 0 }, 'Initial allowance not zero');
    
    // Approve tokens with double the amount to ensure sufficient allowance
    let double_amount = to_u256(2 * MOCK_TOTAL_AMOUNT);
    let success = token.approve(escrow.contract_address, double_amount);
    assert(success, 'Approval failed');
    
    // Debug: Print state after approval
    print_token_state(token, user_address, escrow.contract_address);
    
    // Verify allowance was set
    let post_approve_allowance = token.allowance(user_address, escrow.contract_address);
    assert(post_approve_allowance == double_amount, 'Allowance not set correctly');
    
    // Do deposit
    let success_deposit = escrow.deposit();
    assert(success_deposit, 'Deposit failed');
    
    // Debug: Print final state
    print_token_state(token, user_address, escrow.contract_address);
    
    // Verify allowance was consumed correctly
    let final_allowance = token.allowance(user_address, escrow.contract_address);
    assert(final_allowance == double_amount - amount_u256, 'Wrong allowance consumption');
    
    // Verify escrow received tokens
    let escrow_balance = token.balance_of(escrow.contract_address);
    assert(escrow_balance == amount_u256, 'Escrow did not receive tokens');
}
