# ena-consensus-submission
Submit consensus sequences to ENA through creation of chromosome list files.

## Usage
This script is intended to be used with ena-read-validator, in order to submit consensus sequences to ENA. This is applicable not only to COVID-19 data, but in the future can be used for other small viral genomes.

During submission of consensus sequences, Webin-CLI is required and submission is carried out at the chromosome level in order to successfully submit.

This script creates an appropriate metadata spreadsheet for creation of the manifest files for each of the consensus sequences later during ena-read-validator. Additionally, it creates chromosome list files using the generate_chromlistfile.sh script.

1. Create chromosome list files:
`bash generate_chromlistfile.sh <CONSENSUS_SEQUENCE_HEADERS_FILE>`. The consensus sequence headers file is just a TSV file with assembly headers which would be used as the 'Assembly Name'. Each header is on a new line.

2. Create metadata spreadsheet to be provided as input for ena-read-validator. Note the input requirements for this script.
`python3 create_metadata_spreadsheet.py --help`
