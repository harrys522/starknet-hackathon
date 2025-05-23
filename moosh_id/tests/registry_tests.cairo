// In moosh_id/tests/registry_tests.cairo
#[cfg(test)] // This attribute guards the entire module for testing
mod registry_tests {
    // Import necessary items from your version of snforge_std
    use core::array::{ArrayTrait, Span, SpanTrait};
    use core::poseidon::poseidon_hash_span; // Use Starknet's Poseidon for consistency
    use core::traits::{Into, TryInto};

    // Import your contract's interface and other necessary items
    // Ensure 'moosh_id' is the name of your package in Scarb.toml
    use moosh_id::FalconPublicKeyRegistry::{
        PK_COEFFICIENT_COUNT, IFalconPublicKeyRegistryDispatcher,
        IFalconPublicKeyRegistryDispatcherTrait,
        // Import your contract's Event enum and the specific data struct
        Event as ContractEvent, // Renamed to avoid conflict
        PublicKeyRegisteredEventData,
    };
    use snforge_std::{
        declare, DeclareResultTrait,
        ContractClassTrait, // CheatTarget is not needed for spy_events()
        spy_events, EventSpy,
        EventSpyTrait, EventsFilterTrait, EventSpyAssertionsTrait,
        Event as SnforgeEvent // Renamed to avoid conflict
    };

    // Helper to deploy the contract
    fn deploy() -> IFalconPublicKeyRegistryDispatcher {
        let contract = declare("moosh_id").unwrap().contract_class();
        let (contract_address, _) = contract.deploy(@array![]).unwrap();

        IFalconPublicKeyRegistryDispatcher { contract_address }
    }

    // Helper: Converts a Span<u16> to Array<felt252> for hashing
    // This should match the logic in your contract or be imported if pub.
    fn pk_u16_span_to_felt252_array_for_hash(span_u16: Span<u16>) -> Array<felt252> {
        let mut arr_felt252 = ArrayTrait::new();
        let mut i: usize = 0;
        while i < span_u16.len() {
            ArrayTrait::append(ref arr_felt252, (*span_u16.at(i)).into());
            i += 1;
        }
        arr_felt252
    }

    // Helper: Generates a dummy PK array of the correct length
    fn generate_dummy_pk(start_val: u16) -> Array<u16> {
        let mut pk_vec = ArrayTrait::new();
        let mut i = 0_u32;
        while i < PK_COEFFICIENT_COUNT {
            ArrayTrait::append(ref pk_vec, start_val + i.try_into().unwrap());
            i += 1;
        }
        pk_vec
    }

    #[test]
    fn test_register_and_get_pk_successfully() {
        let mut dispatcher = deploy();
        let pk_to_register_original = generate_dummy_pk(100_u16);

        let mut event_spy = spy_events();

        dispatcher.register_public_key(pk_to_register_original.span());

        let pk_coeffs_felt252_array = pk_u16_span_to_felt252_array_for_hash(
            pk_to_register_original.span(),
        );
        let expected_key_hash = poseidon_hash_span(pk_coeffs_felt252_array.span());

        let retrieved_pk_array = dispatcher.get_public_key(expected_key_hash);

        assert(
            retrieved_pk_array.len() == pk_to_register_original.len(),
            'Retrieved PK length mismatch',
        );
        let mut i: usize = 0;
        while i < pk_to_register_original.len() {
            assert(
                *retrieved_pk_array.at(i) == *pk_to_register_original.at(i), 'PK coeff mismatch',
            );
            i += 1;
        }

        // Construct the expected event for assertion
        // Based on your contract: enum Event { PublicKeyRegistered: PublicKeyRegisteredEventData }
        // Keys: selector("PublicKeyRegistered"), then key_hash from PublicKeyRegisteredEventData
        // Data: pk_coefficient_count from PublicKeyRegisteredEventData
        let mut expected_snforge_event_keys = array![selector!("PublicKeyRegistered")];
        ArrayTrait::append(ref expected_snforge_event_keys, expected_key_hash);

        let mut expected_snforge_event_data = array![PK_COEFFICIENT_COUNT.into()];

        // The event_spy.assert_emitted expects an array of tuples: (from_address,
        // event_name_selector, keys_without_selector, data)
        // OR an array of snforge_std::Event structs. Let's use the struct.
        let expected_emitted_event = SnforgeEvent {
            from_address: dispatcher.contract_address,
            keys: expected_snforge_event_keys,
            data: expected_snforge_event_data,
        };

        event_spy.assert_emitted(@array![expected_emitted_event]);
    }

    #[test]
    #[should_panic(expected: ('PK hash already registered',))]
    fn test_register_duplicate_pk_panics() {
        let mut dispatcher = deploy();
        let pk_to_register = generate_dummy_pk(200_u16);
        dispatcher.register_public_key(pk_to_register.span());
        dispatcher.register_public_key(pk_to_register.span());
    }

    #[test]
    #[should_panic(expected: ('Invalid PK coeff count',))]
    fn test_register_invalid_length_pk_panics() {
        let mut dispatcher = deploy();
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

    #[test]
    #[should_panic(expected: ('PK hash not found',))]
    fn test_get_non_existent_pk_panics() {
        let dispatcher = deploy();
        let non_existent_hash = 123456789123456789_felt252;
        dispatcher.get_public_key(non_existent_hash);
    }
}
