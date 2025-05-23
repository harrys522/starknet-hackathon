# Moosh Starknet Hackathon project

## Idea

Make an on-chain verifier for ZKPs which prove a signature for a shortened (hashed) falcon address.

## Contract 1: Register Identity

Arguments:

* `pk` - The public key
* `n` - the degree of the polynomials

Has exposed functions for Contract 2 to resolve an address to a public key, with STARK proving the hash function was executed correctly.

Requires about 28 slots to store each address from a max of 3000 per contract, for max of 100 addresses.

If each slot is $0.20, it would cost $5.60, but it only needs to be run once by anyone to register the address of a public key.

1. Prove a shortened address is the hash result of the public key.

## Contract 2: Verify message signature for registered identity

Arguments:

* `s1` - Uncompressed signature
* `address` - The id registered in contract 1
* `msg_point` - pre-computed SHAKE(message | salt)
* `n` - the degree of the polynomials

Takes an address and message point to resolve a public key from contract 1 and run verify_uncompressed()

1. Generate a STARK that proves an uncompressed signature was verified for a public key and (msg | salt) content.
2. Verify_compressed(addressTx STARK, sig verify uncompressed STARK) -> ZKP of message signature for shortened address

```cairo
/// Verify a Falcon signature
///
/// # Arguments
/// * `s1` - Uncompressed signature
/// * `pk` - The public key
/// * `msg_point` - pre-computed SHAKE(message | salt)
/// * `n` - the degree of the polynomials
pub fn verify_uncompressed<const N: u32>(
    s1: Span<u16>, pk: Span<u16>, msg_point: Span<u16>, n: u32,
) -> Result<(), FalconVerificationError> {
    assert(s1.len() == n, 'unexpected s1 length');
    assert(pk.len() == n, 'unexpected pk length');
    assert(msg_point.len() == n, 'unexpected msg length');

    let s1_x_h = mul_zq(s1, pk);
    let s0 = sub_zq(msg_point, s1_x_h);

    let norm = extend_euclidean_norm(extend_euclidean_norm(0, s0)?, s1)?;
    if norm > sig_bound(n) {
        return Result::Err(FalconVerificationError::NormOverflow);
    }

    Result::Ok(())
}

register_address(
    pk: Span<u16>, n: u32,
) -> Result<(hashAddress, HashError)> {

}
```

