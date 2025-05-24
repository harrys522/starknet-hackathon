use core::array::ArrayTrait;
use core::traits::TryInto;

use moosh_id::keyregistry::FalconPublicKeyRegistry::{
    PK_COEFFICIENT_COUNT, IFalconPublicKeyRegistryDispatcher,
    IFalconPublicKeyRegistryDispatcherTrait,
};

use super::test_utils::deploy_registry;

#[should_panic]
#[test]
fn test_register_invalid_length_pk_panics() {
    let mut dispatcher = deploy_registry();
    let mut pk_short_vec = ArrayTrait::new();
    if PK_COEFFICIENT_COUNT > 0 {
        let mut i = 0_u32;
        let target_len: u32 = PK_COEFFICIENT_COUNT - 1;
        while i < target_len {
            ArrayTrait::append(ref pk_short_vec, i.try_into().unwrap());
            i += 1;
        }
    } else {
        ArrayTrait::append(ref pk_short_vec, 1_u16);
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