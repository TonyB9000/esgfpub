NOTE:  Only lines 1 and 2 need to be executed.

1.  In the subdirectory "para" use "parallel_sproket.sh" to obtain the publication url-path to every published datafile

    (parallel_sproket.sh creates, for each unique "e3sm" experiment, a unique sun_script keyed to a unique config file,
    and each sub_script plances a runflag in the directory, and removes it upon completion.  The parent script then
    concatenates and sorts the individual results and writes the output to the parent "sproket" directory.

        OutputFile:         E3SM_datafile_urls-<timestamp>
        OutputForm:         (lines of) http(s)://<host>/thredds/fileServer/user_pub_work/<facet_path>/<filename>

    NOTE:       This process can take 5-10 minutes

2.  In this (sproket) directory, run "process_sproket_output.sh E3SM_datafile_urls-<timestamp>" to produce the
    publication report datafiles:

    Produces Outfile:   E3SM_dataset_paths_full-<timestamp>
    Produces Outfile:   E3SM_dataset_paths_leaf-<timestamp>
    Produces Outfile:   E3SM_dataset_ids-<timestamp>

    OutputFile:         ESGF_publication_report-<timestamp>
    OutputForm:         yearspan,filecount,datasetID,firstfile
    
The final "ESGF_publication_report-<timestamp>" is used by several other publlication status reports as input.



