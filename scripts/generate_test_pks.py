from falcon import (
    SecretKey,
)  # Make sure you have the python-falcon library: pip install pyfalcon
import json
import argparse


def generate_falcon_pks(n: int, num_pks: int) -> list:
    """Generates a list of Falcon public keys."""
    pks_data = []
    for i in range(num_pks):
        # Create a new secret key for each PK to ensure variety
        # For a fixed N, this generates different PKs.
        sk = SecretKey(n)
        # sk.h contains the public key coefficients (h_i mod q)
        # These are small integers, suitable for u16.
        pk_coeffs_u16 = [int(coeff) for coeff in sk.h]
        pks_data.append({"pk_id": f"pk_{i + 1}_n{n}", "pk_coefficients": pk_coeffs_u16})
        if i == 0:  # Print the first one for easy copy-pasting into Cairo tests
            print(f"\nSample PK for N={n} (Python list format, copy for Cairo Array):")
            print(f"{pk_coeffs_u16}")
            cairo_array_literal = ", ".join(map(str, pk_coeffs_u16))
            print(
                f"\nCairo array literal (approximate, add _u16 suffix if needed in Cairo):"
            )
            print(f"array![{cairo_array_literal}]")
    return pks_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Falcon public keys for Starknet Cairo testing."
    )
    parser.add_argument(
        "--n",
        type=int,
        required=True,
        help="Degree N for Falcon (e.g., 512, 1024). Must be a power of 2 up to 1024.",
    )
    parser.add_argument(
        "--num_pks",
        type=int,
        default=1,
        help="Number of distinct public keys to generate.",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        help="Output JSON file name. If not provided, defaults to falcon_pks_n<N>_<num_pks>pks.json",
    )

    args = parser.parse_args()

    if args.output_file is None:
        args.output_file = f"falcon_pks_n{args.n}_{args.num_pks}pks.json"

    # Validate N for python-falcon library
    if args.n not in [2**i for i in range(1, 11)]:  # Powers of 2 from 2 to 1024
        raise ValueError(
            f"Unsupported degree N={args.n}. "
            "Supported degrees are powers of 2 from 2 up to 1024 (e.g., 512, 1024)."
        )

    generated_pks_list = generate_falcon_pks(args.n, args.num_pks)

    with open(args.output_file, "w") as f:
        json.dump(generated_pks_list, f, indent=2)

    print(
        f"\nSuccessfully generated {args.num_pks} PK(s) of degree {args.n} and saved to {args.output_file}"
    )
