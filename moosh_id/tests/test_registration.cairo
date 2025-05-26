use core::array::ArrayTrait;
use core::poseidon::poseidon_hash_span;
use core::traits::TryInto;
use moosh_id::keyregistry::FalconPublicKeyRegistry::{
    IFalconPublicKeyRegistryDispatcherTrait, PK_SIZE_512,
};
use snforge_std::{CheatSpan, cheat_caller_address, start_cheat_caller_address_global};
use starknet::ContractAddress;
use super::test_utils::{deploy_registry, generate_dummy_pk, pk_u16_span_to_felt252_array_for_hash};

#[test]
fn test_register_and_get_pk_successfully() {
    let mut dispatcher = deploy_registry();
    let pk_to_register_original = generate_dummy_pk(100_u16, PK_SIZE_512);

    // Register the public key
    dispatcher.register_public_key(pk_to_register_original.span());

    // Calculate the hash for retrieval
    let pk_coeffs_felt252_array = pk_u16_span_to_felt252_array_for_hash(
        pk_to_register_original.span(),
    );
    let expected_key_hash = poseidon_hash_span(pk_coeffs_felt252_array.span());

    // Retrieve and verify
    let retrieved_pk_array = dispatcher.get_public_key(expected_key_hash);

    assert(
        retrieved_pk_array.len() == pk_to_register_original.len(), 'Retrieved PK length mismatch',
    );
    let mut i: usize = 0;
    while i < pk_to_register_original.len() {
        assert(*retrieved_pk_array.at(i) == *pk_to_register_original.at(i), 'PK coeff mismatch');
        i += 1;
    }
}

#[test]
fn test_register_duplicate_pk_panics() {
    let mut dispatcher = deploy_registry();
    let pk_to_register = generate_dummy_pk(200_u16, PK_SIZE_512);
    let success = dispatcher.register_public_key(pk_to_register.span());
    assert(success, 'First registration succeeds');
    let failed_successfully = dispatcher.register_public_key(pk_to_register.span());
    assert(!failed_successfully, 'Second registration should fail');
}

// Helper for distinct actor addresses
fn ACTOR_REGISTRANT() -> ContractAddress {
    12345.try_into().unwrap()
}
fn DEFAULT_DEPLOYER() -> ContractAddress {
    // snforge typically uses address 0 as the default caller/deployer
    // If your setup is different, adjust this.
    0.try_into().unwrap()
}

#[should_panic(expected: ('PK hash not found',))]
#[test]
fn test_get_nonexistent_key_owner_fails() {
    let dispatcher = deploy_registry();
    dispatcher.get_key_owner(1234.into());
}

#[test]
fn test_owner_is_set_correctly_with_default_deployer() {
    start_cheat_caller_address_global(DEFAULT_DEPLOYER());

    let mut dispatcher = deploy_registry(); // Deployed by snforge's default caller
    let owner = dispatcher.get_registry_owner();

    // expected_owner should be the actual default deployer address in your snforge environment.
    // This is typically 0.
    let expected_owner = DEFAULT_DEPLOYER();

    // Your original assertion was failing because `owner` was likely 0 (or another snforge default)
    // and not 1.
    assert(owner == expected_owner, 'Owner should be deployer');
}

#[test]
fn test_key_owner_tracking() {
    start_cheat_caller_address_global(DEFAULT_DEPLOYER());
    // 1. Deploy the contract. It's deployed by DEFAULT_DEPLOYER().
    let mut dispatcher = deploy_registry();
    // We need the address of the deployed contract to target it with cheat_caller_address.
    // Ensure your `dispatcher` object can provide its contract address.
    // This might be `dispatcher.contract_address` or a method like `dispatcher.get_address()`.
    // Let's assume `dispatcher.contract_address` exists.
    let registry_address = dispatcher.contract_address;

    // 2. Define the actor who will register the public key.
    let registrant_actor = ACTOR_REGISTRANT();

    // 3. Prepare the public key.
    let pk_to_register = generate_dummy_pk(300_u16, PK_SIZE_512);

    // 4. Use cheat_caller_address to make `registrant_actor` the caller
    //    for the `register_public_key` method.
    cheat_caller_address(
        registry_address, // Target contract: your deployed registry
        registrant_actor, // Caller to simulate
        CheatSpan::TargetCalls(1) // Apply only for the next call to registry_address
    );

    // 5. Call register_public_key. The contract will see `registrant_actor` as the caller.
    dispatcher.register_public_key(pk_to_register.span());

    // 6. Calculate the key hash.
    let pk_coeffs_felt252_array = pk_u16_span_to_felt252_array_for_hash(pk_to_register.span());
    let key_hash = poseidon_hash_span(pk_coeffs_felt252_array.span());

    // 7. Retrieve the key owner.
    let key_owner = dispatcher.get_key_owner(key_hash);

    // 8. Assert that the key owner is the `registrant_actor`.
    // This should now pass because the registration was done by `registrant_actor`.
    assert(key_owner == registrant_actor, 'Key owner must be registrant');
}
