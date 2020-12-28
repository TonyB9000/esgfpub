To conduct archive extraction more easily and prepare for the "state-machine" way of doing things, I have revamped that process.

OVERVIEW:  A "State-Machine Compliant" method of archive extraction has replaced the previous methodology (see HISTORY below for details).

A background "archive_extraction_service.py" has been implemented to operate over a "request queue" (/p/user_pub/e3sm/archive/.extraction_requests/).
(This parallels the "mapfile_generation_service.py" that calls "esgmapfile make" sequentially to avoid possible I/O binding or mishandling until slurm.)

As mentionned below in HISTORY, a complicating factor in archive extraction that does not present itself in most other workflows that that a "dataset" is
not 1-to-1 with an archive location but may require 2 or more separate extractions (and zstash calls) to collect the files representing a complete dataset.

Feeding this background archive extractor (submitting extraction requests) is made easier, as there is no longer a "jobset config" that must be edited.
The "resolution" value is automatically determined.  All that is needed is to supply a list of Archive_Map lines (/p/user_pub/e3sm/archive/.cfg/Archive_Map)
to a utility called

    archive_map_to_dsid.py  --input file_of_archive_map_lines [--names | --files] [--prefix]

This utility serves different purposes.  If you only want to know what "dataset_id" corresponds to a given Archive Map line (or lines)

    archive_map_to_dsid.py  --input file_of_archive_map_lines –names

will produce the dataset IDs to stdout.  If you want to submit "archive extraction" requests, use

    archive_map_to_dsid.py  --input file_of_archive_map_lines –prefix "extraction_request-"

This will produce a series of extraction request files

    extraction_request-<dsid1>
    extraction_request-<dsid2>
    . . .

Each request will contain the Archive_Map line (or lines if multiples are required) to guide the extraction to warehouse.
Simply move these to the archive extraction request queue,

    /p/user_pub/e3sm/archive/.extraction_requests/

and they should be picked up automatically.


The Archive_Extraction Loop-Process:

In place of 

    publication_staging_control.py
    archive_publication_stager.py

There is now the single background process

    archive_extraction_service.py

This process mimics most of what we refer to in the state machine as the EXTRACTION workflow, and contains the following subordinate processes,
each of which can have the "Ready", "Engaged", "Pass" or "Fail" status:

    EXTRACTION:SETUP
        Opens an extraction request file, calculates warehouse destination facet path.
        Determines if the path already exists, creates the path if needed.
        Determines if the .status file exists, creates an initial one if needed.

    EXTRACTION:ZSTASH
        For each Archive_Map line supplied for this single dataset, the Holodeck is cleared and reset for zstash extraction
        zstash is engaged
        ZSTASH:[Pass|Fail] is returned

    EXTRACTION:TRANSFER
        The zstash-extracted files are moved to their warehouse destination.

This "archive_extraction_service" (as with "warehouse_assign", "warehouse_publication") mimics the state machine operation only in that it

    (a) tends to process each job independently  (vertically, as opposed to horizontally, except at the very top to reduce the submission burden, and
    (b) reads and writes to the dataset .status file, conforming to conditions it finds in terms of locks, blocks, "Ready", "Pass", "Fail", etc.

Therefore, it takes on the role of "Warehouse", or "Extraction" (or subordinate processes) as needed to mimic what would often be asynchronous operations.


HISTORY:

A complicating factor in archive extraction that does not present itself in most other workflows that that a "dataset" is not 1-to-1 with an archive location but may require 2 or more separate extractions (and zstash calls) to collect the files representing a complete dataset.

Previously I employed two python scripts to conduct multi-dataset extraction:

    publication_staging_control.py
        This would accept an input list of as many Archive_Map lines as needed to extract some number of datasets.
        For each line, determine the (warehouse) faceted destination path (resolution constant![*])
        Call archive_publication_stager.py to manage the holodeck setup, zstash extraction, and file transfer.
        Wait for return before processing another archive map line.

    archive_publication_stager.py
        This would accept a SINGLE archive path, dataset extraction pattern, and destination facet-path.
        It would set up the "Holodeck" of symlinks amenable to zstash (and ensure proper zstash version)
        Activate "zstash extract", and wait for completion.
        Transfer the extracted files to their intended warehouse (faceted path) destination.

        [*] Note, although the archive map line contained the archive name, I never keyed in to using the "ne30" or "ne120"
        embedded in the name to automatically select the resolution, and instead required that the entire run use a "jobset"
        config file, that specified the resolution.  This meant that you could not extract both low-res and high-res datasets
        in a multi-dataset extraction.

