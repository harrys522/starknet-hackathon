# shell.nix
{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python311 # Or your chosen Python version
    pkgs.gcc
    pkgs.zlib
    pkgs.freetype
    pkgs.libpng
    pkgs.pkg-config
    pkgs.gmp # Added GMP
  ];

  shellHook = ''
    export NIX_LD_LIBRARY_PATH="${
      pkgs.lib.makeLibraryPath [
        pkgs.stdenv.cc.cc.lib # Provides libstdc++.so.6 from gcc
        pkgs.zlib
        pkgs.freetype
        pkgs.libpng
        pkgs.gmp # Ensure GMP's lib directory is included
      ]
    }"
    if [ -n "$LD_LIBRARY_PATH" ]; then
      export LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH:$LD_LIBRARY_PATH"
    else
      export LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH"
    fi

    echo "--- Nix Shell Environment Initialized (with GMP) ---"
    echo "Python: $(which python3)"
    echo "GCC: $(which gcc)"
    # The following line is for debugging and can be removed if too verbose later
    # echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
    echo "--- You can now (re)activate your .venv and (re)install packages ---"
  '';
}
