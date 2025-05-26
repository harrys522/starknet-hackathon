# shell.nix
{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python311
    pkgs.gcc # For G++ compiler and libstdc++.so.6
    pkgs.zlib # For PNG support in matplotlib and other libraries
    pkgs.freetype # For font rendering (e.g., matplotlib)
    pkgs.pkg-config # To help find libraries during build
    # Add other system-level build dependencies if they arise
  ];

  # Optional: You can also try explicitly setting LD_LIBRARY_PATH here
  # though Nix usually handles this through wrappers or rpaths.
  shellHook = ''
    # Construct the library path from specified nix packages
    # pkgs.lib.makeLibraryPath is a helper function to correctly list library directories
    export NIX_LD_LIBRARY_PATH="${
      pkgs.lib.makeLibraryPath [
        pkgs.stdenv.cc.cc.lib # This provides libstdc++.so.6
        pkgs.zlib
        pkgs.freetype
        pkgs.libpng
      ]
    }"

    # Prepend Nix library path to any existing LD_LIBRARY_PATH
    if [ -n "$LD_LIBRARY_PATH" ]; then
      export LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH:$LD_LIBRARY_PATH"
    else
      export LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH"
    fi

    echo "--- Nix Shell Environment Initialized ---"
    echo "Python: $(which python3)"
    echo "GCC: $(which gcc)"
    echo "LD_LIBRARY_PATH has been set to: $LD_LIBRARY_PATH"
    echo "Test for libstdc++.so.6 in NIX_LD_LIBRARY_PATH:"
    (IFS=:; for path in $NIX_LD_LIBRARY_PATH; do if [ -f "$path/libstdc++.so.6" ]; then echo "Found libstdc++.so.6 in $path"; break; fi; done;)
    echo "--- You can now create/activate your .venv and install packages ---"
    source .venv/bin/activate
  '';
}
