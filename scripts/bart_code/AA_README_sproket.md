
Use sproket_search.sh to obtain the publication url-path to every published datafile

    OutputFile:         E3SM_datafile_urls-<timestamp>
    OutputForm:         http(s)://<host>/thredds/fileServer/user_pub_work/<facet_path>/<filename>

    NOTE:       This process can take several hours

Issue: cat E3SM_datafile_urls | cut -f7- -d/ | sort | uniq > E3SM_dataset_paths_full

Issue: cat E3SM_dataset_paths_full | rev | cut -f2- -d/ | rev | sort | uniq > E3SM_dataset_paths_leaf

Issue: cat E3SM_dataset_paths_leaf | tr / . > E3SM_dsids

Use: process_sproket_output.sh E3SM_datafile_urls-<timestamp> to produce the publication report data

    Produces Outfile:   E3SM_dataset_paths_full-<timestamp>
    Produces Outfile:   E3SM_dataset_paths_leaf-<timestamp>
    Produces Outfile:   E3SM_dataset_ids-<timestamp>

    OutputFile:         ESGF_publication_report-<timestamp>
    OutputForm:         yearspan,filecount,datasetID,firstfile
    


