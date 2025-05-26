from falcon import SecretKey, decompress, HEAD_LEN, SALT_LEN
import argparse

Q = 12289


def generate_attestations(n: int, num_signatures: int) -> list[dict]:
    sk = SecretKey(n)
    attestations = [
        generate_attestation(sk, f"message #{i}".encode())
        for i in range(num_signatures)
    ]
    return attestations


def generate_attestation(sk: SecretKey, message: bytes):
    signature = sk.sign(message)
    salt = signature[HEAD_LEN : HEAD_LEN + SALT_LEN]
    enc_s = signature[HEAD_LEN + SALT_LEN :]
    s1 = decompress(enc_s, sk.sig_bytelen - HEAD_LEN - SALT_LEN, sk.n)
    msg_point = sk.hash_to_point(message, salt)
    return {"s1": [x % Q for x in s1], "pk": sk.h, "msg_point": msg_point}


def format_array(arr: list, name: str, size: int) -> str:
    # Format array with 14 elements per line for readability
    elements_per_line = 14
    lines = []
    for i in range(0, len(arr), elements_per_line):
        chunk = arr[i : i + elements_per_line]
        lines.append("    " + ", ".join(str(x) for x in chunk) + ",")

    return f"pub const {name}: [u16; {size}] = [\n" + "\n".join(lines) + "\n];\n"


def format_args(args: list[dict], n: int):
    if len(args) == 0:
        return "No attestations generated"

    # Take the first attestation
    arg = args[0]

    # Format each array
    pk_array = format_array(arg["pk"], "PK_N" + str(n), n)
    s1_array = format_array(arg["s1"], "S1_N" + str(n), n)
    msg_point_array = format_array(arg["msg_point"], "MSG_POINT_N" + str(n), n)

    # Combine all arrays with comments
    result = "// Test vectors for Falcon signature verification\n\n"
    result += "// Public key coefficients\n" + pk_array + "\n"
    result += "// Signature coefficients (s1)\n" + s1_array + "\n"
    result += "// Message point coefficients\n" + msg_point_array

    # Write to a file
    with open(f"moosh_id/tests/inputs/falcon_test_vectors_n{n}.cairo", "w") as f:
        f.write(result)

    return f"Test vectors have been written to falcon_test_vectors_n{n}.cairo"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=512)
    parser.add_argument("--num_signatures", type=int, default=1)
    args = parser.parse_args()

    attestations = generate_attestations(args.n, args.num_signatures)
    print(format_args(attestations, args.n))
