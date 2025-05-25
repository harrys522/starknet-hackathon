use core::poseidon::poseidon_hash_span;
use snforge_std::{declare, ContractClassTrait, DeclareResultTrait};

// Import our contracts
use moosh_id::keyregistry::FalconPublicKeyRegistry::{
    IFalconPublicKeyRegistryDispatcherTrait
};
use moosh_id::addressverifier::FalconSignatureVerifier::{
    IFalconSignatureVerifierDispatcher,
    IFalconSignatureVerifierDispatcherTrait
};

use super::test_utils::{deploy_registry, pk_u16_span_to_felt252_array_for_hash};

// Import test vectors
use super::inputs::falcon_test_vectors_n512::{PK_N512, S1_N512, MSG_POINT_N512};
use super::inputs::falcon_test_vectors_n1024::{PK_N1024, S1_N1024, MSG_POINT_N1024};

#[test]
fn test_verify_n512() {
    // First deploy the registry
    let registry = deploy_registry();
    
    // Then deploy the verifier, passing the registry's address
    let verifier_contract = declare("FalconSignatureVerifier").unwrap().contract_class();
    let (verifier_address, _) = verifier_contract
        .deploy(@array![registry.contract_address.into()])
        .unwrap();
    
    let verifier = IFalconSignatureVerifierDispatcher { 
        contract_address: verifier_address 
    };

    // Convert spans for easier access
    let pk_span = PK_N512.span();
    let s1_span = S1_N512.span();
    let msg_point_span = MSG_POINT_N512.span();
    
    // Register the public key
    let success = registry.register_public_key(pk_span);
    assert(success, 'Registration should succeed');

    // Get the key hash
    let pk_felts = pk_u16_span_to_felt252_array_for_hash(pk_span);
    let key_hash = poseidon_hash_span(pk_felts.span());

    // Verify the signature
    let result = verifier.verify_signature_for_key_hash(
        key_hash,
        s1_span,
        msg_point_span
    );

    assert(result == true, 'Signature verification failed');
}

#[test]
fn test_verify_n1024() {
    // First deploy the registry
    let registry = deploy_registry();
    
    // Then deploy the verifier, passing the registry's address
    let verifier_contract = declare("FalconSignatureVerifier").unwrap().contract_class();
    let (verifier_address, _) = verifier_contract
        .deploy(@array![registry.contract_address.into()])
        .unwrap();
    
    let verifier = IFalconSignatureVerifierDispatcher { 
        contract_address: verifier_address 
    };

    // Convert spans for easier access
    let pk_span = PK_N1024.span();
    let s1_span = S1_N1024.span();
    let msg_point_span = MSG_POINT_N1024.span();
    
    // Register the public key
    let success = registry.register_public_key(pk_span);
    assert(success, 'Registration should succeed');

    // Get the key hash
    let pk_felts = pk_u16_span_to_felt252_array_for_hash(pk_span);
    let key_hash = poseidon_hash_span(pk_felts.span());

    // Verify the signature
    let result = verifier.verify_signature_for_key_hash(
        key_hash,
        s1_span,
        msg_point_span
    );

    assert(result == true, 'Signature verification failed');
}
