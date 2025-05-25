use core::array::ArrayTrait;
use core::traits::TryInto;

use moosh_id::keyregistry::FalconPublicKeyRegistry::{
    IFalconPublicKeyRegistryDispatcherTrait,
    PK_SIZE_512
};

use super::test_utils::deploy_registry;

#[should_panic]
#[test]
fn test_register_invalid_length_pk_panics() {
    let mut dispatcher = deploy_registry();
    let mut pk_short_vec = ArrayTrait::new();
    let target_len: u32 = PK_SIZE_512 - 1;
    let mut i = 0_u32;
    while i < target_len {
        ArrayTrait::append(ref pk_short_vec, i.try_into().unwrap());
        i += 1;
    }
    dispatcher.register_public_key(pk_short_vec.span());
}

#[should_panic]
#[test]
fn test_get_non_existent_pk_panics() {
    let dispatcher = deploy_registry();
    let non_existent_hash = 123456789123456789_felt252;
    dispatcher.get_public_key(non_existent_hash);
} 