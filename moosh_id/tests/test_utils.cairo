use core::array::{ArrayTrait, Span, SpanTrait};
use core::poseidon::poseidon_hash_span;
use core::traits::{Into, TryInto};

use moosh_id::keyregistry::FalconPublicKeyRegistry::{
    IFalconPublicKeyRegistryDispatcher,
    IFalconPublicKeyRegistryDispatcherTrait,
    PK_SIZE_512, PK_SIZE_1024
};
use snforge_std::{declare, ContractClassTrait, DeclareResultTrait};

/// Deploys a new instance of the FalconPublicKeyRegistry contract
pub fn deploy_registry() -> IFalconPublicKeyRegistryDispatcher {
    let contract = declare("FalconPublicKeyRegistry").unwrap().contract_class();
    let (contract_address, _) = contract.deploy(@array![]).unwrap();
    IFalconPublicKeyRegistryDispatcher { contract_address }
}

/// Converts a Span of u16 values to an Array of felt252 values for hashing
pub fn pk_u16_span_to_felt252_array_for_hash(span_u16: Span<u16>) -> Array<felt252> {
    let mut arr_felt252 = ArrayTrait::new();
    let mut i: usize = 0;
    while i < span_u16.len() {
        ArrayTrait::append(ref arr_felt252, (*span_u16.at(i)).into());
        i += 1;
    }
    arr_felt252
}

/// Generates a dummy public key array starting from a given value
/// size must be either 512 or 1024
pub fn generate_dummy_pk(start_val: u16, size: u32) -> Array<u16> {
    assert(size == PK_SIZE_512 || size == PK_SIZE_1024, 'Invalid key size');
    let mut pk_vec = ArrayTrait::new();
    let mut i = 0_u32;
    while i < size {
        ArrayTrait::append(ref pk_vec, start_val + i.try_into().unwrap());
        i += 1;
    }
    pk_vec
} 

// 