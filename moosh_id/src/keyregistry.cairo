// SPDX-FileCopyrightText: 2025 Yerbacorp Pty Ltd
//
// SPDX-License-Identifier: MIT

#[starknet::contract]
pub mod FalconPublicKeyRegistry {
    use core::array::{ArrayTrait, SpanTrait};
    use core::option::{Option, OptionTrait};
    use core::panic_with_felt252;
    use core::poseidon::poseidon_hash_span;
    use core::traits::{Into, TryInto};
    use starknet::storage::{Map, StorageMapReadAccess, StorageMapWriteAccess};

    // --- Constants ---
    pub const PK_SIZE_512: u32 = 512;
    pub const PK_SIZE_1024: u32 = 1024;

    // --- Storage ---
    #[storage]
    struct Storage {
        pk_metadata: Map<felt252, u32>,
        pk_coefficients: Map<(felt252, u32), u16>,
    }

    // --- Event Data Structures ---
    #[derive(Drop, starknet::Event)]
    pub struct PublicKeyRegisteredEventData {
        #[key]
        key_hash: felt252,
        pk_coefficient_count: u32,
    }

    // --- Main Event Enum for the Contract ---
    #[event]
    #[derive(Drop, starknet::Event)]
    pub enum Event {
        PublicKeyRegistered: PublicKeyRegisteredEventData,
    }

    // --- Helper Functions ---
    fn u16_span_to_felt252_array(span_u16: Span<u16>) -> Array<felt252> {
        let mut arr_felt252 = ArrayTrait::new();
        let mut i: usize = 0;
        while i < span_u16.len() {
            ArrayTrait::append(ref arr_felt252, (*span_u16.at(i)).into());
            i += 1;
        }
        arr_felt252
    }

    // --- Contract Interface (ABI) ---
    #[starknet::interface]
    pub trait IFalconPublicKeyRegistry<TContractState> {
        fn register_public_key(ref self: TContractState, pk_coefficients_span: Span<u16>) -> bool;
        fn get_public_key(self: @TContractState, key_hash: felt252) -> Array<u16>;
    }

    // --- Contract Implementation ---
    #[abi(embed_v0)]
    impl FalconPublicKeyRegistryImpl of IFalconPublicKeyRegistry<ContractState> {
        fn register_public_key(ref self: ContractState, pk_coefficients_span: Span<u16>) -> bool {
            // Validate key size (must be either 512 or 1024)
            let pk_len: u32 = pk_coefficients_span.len().try_into().unwrap();
            assert(pk_len == PK_SIZE_512 || pk_len == PK_SIZE_1024, 'Invalid PK size');

            let pk_coeffs_felt252_array = u16_span_to_felt252_array(pk_coefficients_span);
            let key_hash = poseidon_hash_span(pk_coeffs_felt252_array.span());

            // Map::read returns V (u32 here), or V::default() (0 for u32) if not found.
            let existing_pk_length: u32 = self.pk_metadata.read(key_hash);

            // If existing_pk_length is not 0, it means the key was found (assuming 0 is not a valid
            // PK_COEFFICIENT_COUNT)
            if existing_pk_length != 0 {
                assert(
                    existing_pk_length == PK_SIZE_512 || existing_pk_length == PK_SIZE_1024, 'Registered length mismatch',
                ); // Optional: sanity check
                return false; // Key already exists
            }

            // Key not found, proceed with registration
            self.pk_metadata.write(key_hash, pk_len);
            let mut i: u32 = 0;
            while i < pk_len {
                let coeff_val = *pk_coefficients_span.at(i.try_into().unwrap());
                self.pk_coefficients.write((key_hash, i), coeff_val);
                i += 1;
            }

            self
                .emit(
                    Event::PublicKeyRegistered(
                        PublicKeyRegisteredEventData {
                            key_hash, pk_coefficient_count: pk_len,
                        },
                    ),
                );

            true // Registration successful
        }

        fn get_public_key(self: @ContractState, key_hash: felt252) -> Array<u16> {
            // Map::read returns V (u32 here), or V::default() (0 for u32) if not found.
            let stored_length: u32 = self.pk_metadata.read(key_hash);

            // If stored_length is 0, it means the key was not found (assuming 0 is not a valid
            // PK_COEFFICIENT_COUNT)
            if stored_length == 0 {
                panic_with_felt252('PK hash not found');
            }

            // If we reach here, the key was found.
            assert(stored_length == PK_SIZE_512 || stored_length == PK_SIZE_1024, 'Stored PK length mismatch');

            let mut coefficients_array = ArrayTrait::new();
            let mut i: u32 = 0;
            while i < stored_length { // Loop up to the known PK_COEFFICIENT_COUNT
                let coeff_val = self.pk_coefficients.read((key_hash, i));
                ArrayTrait::append(ref coefficients_array, coeff_val);
                i += 1;
            }
            coefficients_array
        }
    }
}
