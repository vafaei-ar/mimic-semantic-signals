#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 DATASET PHYSIONET_USERNAME" >&2
  echo "Datasets: eicu, nwicu, mimic-br, hirid, sicdb" >&2
  exit 2
fi

dataset="$1"
username="$2"
base="$HOME/datasets/external_icu"

case "$dataset" in
  eicu)
    slug="eicu-crd"
    version="2.0"
    target="$base/eicu"
    ;;
  nwicu)
    slug="nwicu-northwestern-icu"
    version="0.1.0"
    target="$base/nwicu"
    ;;
  mimic-br)
    slug="mimic-br"
    version="1.0.1"
    target="$base/mimic_br"
    ;;
  hirid)
    slug="hirid"
    version="1.1.1"
    target="$base/hirid"
    ;;
  sicdb)
    slug="sicdb"
    version="1.0.8"
    target="$base/sicdb"
    ;;
  *)
    echo "Unknown dataset: $dataset" >&2
    echo "Datasets: eicu, nwicu, mimic-br, hirid, sicdb" >&2
    exit 2
    ;;
esac

mkdir -p "$target"
cd "$target"

url="https://physionet.org/files/$slug/$version/"

echo "Dataset: $dataset"
echo "Destination: $target"
echo "Source: $url"
echo "PhysioNet will prompt for the password for user: $username"

wget -r -N -c -np -nH --cut-dirs=2   --user "$username"   --ask-password   "$url"

echo
echo "Download completed or resumed."
find "$target" -maxdepth 3 -type f | sort | head -n 40
