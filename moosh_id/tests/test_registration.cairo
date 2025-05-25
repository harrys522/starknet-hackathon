use core::array::{ArrayTrait};
use core::poseidon::poseidon_hash_span;

use moosh_id::keyregistry::FalconPublicKeyRegistry::{
    IFalconPublicKeyRegistryDispatcherTrait,
    PK_SIZE_512
};

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
        retrieved_pk_array.len() == pk_to_register_original.len(),
        'Retrieved PK length mismatch',
    );
    let mut i: usize = 0;
    while i < pk_to_register_original.len() {
        assert(
            *retrieved_pk_array.at(i) == *pk_to_register_original.at(i),
            'PK coeff mismatch',
        );
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