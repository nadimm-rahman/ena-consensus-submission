#!/usr/bin/python3

# Script to create a metadata spreadsheet for batch submission of the Dutch consensus sequences.

# IMPROVEMENTS:
#   --> Add to generate_chromlistfile.sh to include a list of fasta files.

# INSTALLATION AND SETUP:
# Requires installation of cx_Oracle: https://cx-oracle.readthedocs.io/en/latest/user_guide/installation.html
# Along with this, the Oracle Instant Client is also required. Download this and then save the directory as an environment variable.
# Alternatively, provide the full path in the initialisation object in this script (edit the line with the following code) --> cx_Oracle.init_oracle_client(lib_dir=PATH_TO_CLIENT)
# Note for Mac: Workaround for security issues --> http://oraontap.blogspot.com/2020/01/mac-os-x-catalina-and-oracle-instant.html#:~:text=Developer%20Cannot%20be%20Verified&text=You%20can%20go%20to%20the,also%20has%20to%20be%20approved.

# Oracle Client EXAMPLE = '/Users/rahman/Downloads/instantclient_19_3'
import pandas as pd
import argparse, cx_Oracle, os, sys
from getpass import getpass


def get_args():
    """
    Get arguments that are passed to the script
    :return: Arguments
    """
    parser = argparse.ArgumentParser(description="""
        + ===================================================================== +
        |  create_metadata_spreadsheet.py                                       |
        |  Tool which creates a metadata spreadsheet to be passed into batch    |
        |  validation/submission.                                               |
        + ===================================================================== +
        """, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-p', '--project', type=str, help='Project ID to obtain metadata for', required=True)
    parser.add_argument('-n', '--names', type=str,
                        help='Consensus/assembled sequence header names to be included as assembly names. Format: List of consensus/assembled sequence headers - one per line',
                        required=True)
    parser.add_argument('-c', '--chromosome_list', type=str,
                        help='Chromosome list files created to be used in submission. Format: List of names of chromosome list files - one per line',
                        required=True)
    parser.add_argument('-f', '--fasta_files', type=str,
                        help='Fasta files of assembled/consensus sequence to be submitted. Format: List of names of fasta files - one per line',
                        required=True)

    args = parser.parse_args()
    return args


class MetadataFromDatabase:
    # Class object which handles obtaining metadata from ERAPRO database
    def __init__(self, project, sql_query):
        self.project = project  # Project ID
        self.query = sql_query  # SQL query to obtain metadata

    def get_oracle_usr_pwd(self):
        """
        Obtain credentials to create an SQL connection
        :return: Username and password for a valid SQL database account
        """
        self.usr = input("Username: ")  # Ask for username
        self.pwd = getpass()  # Ask for password and handle appropriately

    def setup_connection(self):
        """
        Set up the database connection
        :return: Database connection object
        """
        client_lib_dir = os.getenv('ORACLE_CLIENT_LIB')
        if not client_lib_dir or not os.path.isdir(client_lib_dir):
            sys.stderr.write("ERROR: Environment variable $ORACLE_CLIENT_LIB must point at a valid directory\n")
            exit(1)
        cx_Oracle.init_oracle_client(lib_dir=client_lib_dir)
        self.connection = None
        try:
            dsn = cx_Oracle.makedsn("ora-vm-009.ebi.ac.uk", 1541,
                                    service_name="ERAPRO")  # Try connection to ERAPRO with credentials
            self.connection = cx_Oracle.connect(self.usr, self.pwd, dsn, encoding="UTF-8")
        except cx_Oracle.Error as error:
            print(error)

    def fetch_metadata(self):
        """
        Obtain metadata from ERAPRO database
        :return: Dataframe of metadata
        """
        self.get_oracle_usr_pwd()  # Obtain credentials from script operator
        self.setup_connection()  # Set up the database connection using the credentials
        if self.connection is not None:
            cursor = self.connection.cursor()
            search_query = cursor.execute(self.query)  # Query the database with the SQL query
            df = pd.DataFrame(search_query.fetchall())  # Fetch all results and save to dataframe
            df.columns = ['study_accession', 'sample_accession', 'run_accession']  # Add column headers to the dataframe
            return df


def create_reference_column(df, final_columns):
    """
    Create (add) a reference column for later joining with project metadata
    :param df: Pandas dataframe to be processed to include a new reference column
    :param final_columns: List of final columns of linked data should look like (e.g. ['FASTA', 'run_accession'])
    :return:
    """
    linked_data = pd.DataFrame(columns=final_columns)
    for index, row in df.iterrows():
        item = row[0]  # This is the item that is to be linked to the project metadata
        if 'FASTA' in final_columns:
            # For fasta files, the separator was '.', whereas others were separated by '_'
            run = item.split('.')[0]  # This is the run to link to, referred in the name of the item
        else:
            run = item.split('_')[0]  # This is the run to link to, referred in the name of the item
        intermediate = pd.DataFrame([[item, run]], columns=final_columns)
        linked_data = linked_data.append(intermediate, ignore_index=True)
    return linked_data


if __name__ == '__main__':
    args = get_args()

    sql_query = "SELECT proj.project_id, samp.sample_id, ru.run_id FROM project proj \
                    JOIN study stu ON (proj.project_id = stu.project_id) \
                    JOIN experiment exp ON (stu.study_id = exp.study_id) \
                    JOIN experiment_sample expsamp ON (exp.experiment_id = expsamp.experiment_id) \
                    JOIN sample samp ON (expsamp.sample_id = samp.sample_id) \
                    JOIN run ru ON (exp.experiment_id = ru.experiment_id) \
                        WHERE proj.project_id='{}'".format(args.project)

    # Get project metadata
    metadata = MetadataFromDatabase(args.project, sql_query)
    project_data = metadata.fetch_metadata()

    # Read in all the data
    assembly_names = pd.read_csv(args.names, sep="\t", header=None)
    chromosome_lists = pd.read_csv(args.chromosome_list, sep="\t", header=None)
    fasta_files = pd.read_csv(args.fasta_files, sep="\t", header=None)

    # STEP 1 --> Create run accession columns for each dataframe to enable for merging with main dataframe
    # Create column for the fasta file defining the corresponding run
    linked_fasta_files = create_reference_column(fasta_files, ['FASTA', 'run_accession'])

    # Create column for the assembly names defining the corresponding run
    linked_assembly_names = create_reference_column(assembly_names, ['ASSEMBLYNAME', 'run_accession'])

    # Create column for the chromosome list file names defining the corresponding run
    linked_chromosome_lists = create_reference_column(chromosome_lists, ['CHROMOSOME_LIST', 'run_accession'])

    # STEP 2 --> Create a dataframe of the preset paramaters
    values = ['COVID-19 outbreak', 30, 'Minimap2', 'OXFORD_NANOPORE', 1, 'genomic DNA']
    parameter_values = [values for _ in range(len(project_data))]
    set_parameters = pd.DataFrame(parameter_values,
                                  columns=['ASSEMBLY_TYPE', 'COVERAGE', 'PROGRAM', 'PLATFORM', 'MINGAPLENGTH',
                                           'MOLECULETYPE'])

    # STEP 3 --> Merge dataframes together
    project_assembly = pd.merge(project_data, linked_assembly_names,
                                on='run_accession')  # Include the assembly name information
    project_assembly = pd.concat([project_assembly, set_parameters], axis=1,
                                 sort=False)  # Include all the other set columns
    project_assembly_fasta = pd.merge(project_assembly, linked_fasta_files,
                                      on='run_accession')  # Include the names of fasta files
    total_metadata = pd.merge(project_assembly_fasta, linked_chromosome_lists,
                              on='run_accession')  # Include the names of chromosome list files

    total_metadata = total_metadata.rename(columns={"study_accession": "STUDY", "sample_accession": "SAMPLE",
                                                    "run_accession": "RUN_REF"})  # Change column names to match the manifest file headers
    metadata_filename = args.project + "_Consensus_Metadata-TEST.txt"
    total_metadata.to_csv(metadata_filename, sep="\t", index=False)