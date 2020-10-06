The Goal of the ArchivePathMapper is to produce new entries for the "Archive_Map" (/p/user_pub/e3sm/archive/.cfg/Archive_Map).  Specifically,

For any required publication of a [ CAMPAIGN MODEL EXPERIMENT ENSEMBLE (realm gridtype freq) ], we will have a table of (one or more) entries

    CAMPAIGN,MODEL,EXPERIMENT,ENSEMBLE,realm_gridtype_freq,archivePath,tarfilePath+extractionPattern

And these entries can be used to drive the data extraction process.

Motivation: 

Each project has idiosyncracies regarding how they tar-up their simulation output, broken down by experiment and dataset type.
The Archive_Map codifies these specifics in a machine-readable format.

Now a single utility:  Usage:

    archive_path_mapper.py -a <file_of_selected_archive_locator_lines>

It takes as input a single file, containing selected lines from the Archive_Locator (/p/user_pub/e3sm/archive/.cfg/Archive_Locator), each
indicating a single (typically new) zstash archive.  The format of Archive_Locator lines is

    CAMPAIGN,MODEL,EXPERIMENT,ENSEMBLE,archivePath

Example:

    BGC-v1,1_1,piControl,ens1,/p/user_pub/e3sm/archive/1_1/BGC-v1/20191204.CNTL_CNPCTC1850_OIBGC.ne30_oECv3.compy
    BGC-v1,1_1,ssp585-BCRC,ens1,/p/user_pub/e3sm/archive/1_1/BGC-v1/20191107.BCRC_CNPCTC_SSP585_OIBGC.ne30_oECv3.compy
    BGC-v1,1_1,ssp585-BCRD,ens1,/p/user_pub/e3sm/archive/1_1/BGC-v1/20191204.BCRD_CNPCTC_SSP585_OIBGC.ne30_oECv3.compy
    BGC-v1,1_1,ssp585-BDRC,ens1,/p/user_pub/e3sm/archive/1_1/BGC-v1/20191107.BDRC_CNPCTC_SSP585_OIBGC.ne30_oECv3.compy
    BGC-v1,1_1,ssp585-BDRD,ens1,/p/user_pub/e3sm/archive/1_1/BGC-v1/20191204.BDRD_CNPCTC_SSP585_OIBGC.ne30_oECv3.compy

For each listed archive, the process cycles over the Standard Dataset Extraction Patterns

(*.cam.h0*, *.clm2.h1*, etc) and repeatedly calls "zstash ls"
to address the appropriate "index.db", and obtains all matching filenames.
For each such dataset pattern, the matching filenames are written to a funny-named output file created in a "PathsFound" directory, such as

    1:BGC-v1:1_1_ECA:piControl:ens1:atm_nat_mon:|p|user_pub|e3sm|archive|1_1_ECA|BGC-v1|20190308.CNTL.1850-2014
    1:BGC-v1:1_1_ECA:piControl:ens1:ocn_nat_5day_snap:|p|user_pub|e3sm|archive|1_1_ECA|BGC-v1|CNTL_CNPECACNT_SSP85.ne30_oECv3.cori-knl
    1:BGC-v1:1_1_ECA:piControl:ens1:sea-ice_nat_mon:|p|user_pub|e3sm|archive|1_1_ECA|BGC-v1|CNTL_CNPECACNT_SSP85.ne30_oECv3.cori-knl

Each of these files may contain both appropriate and inappropriate matches.

Subsequently (stage 2), the process opens these oddly-named files, and writes selected lines to a single output file "headset_list_first_last". 
For each oddly-named file, it first writes the filename, but only after conversion from

     1:BGC-v1:1_1_ECA:piControl:ens1:atm_nat_mon:|p|user_pub|e3sm|archive|1_1_ECA|BGC-v1|20190308.CNTL.1850-2014
to
     BGC-v1,1_1_ECA,piControl,ens1,atm_nat_mon,/p/user_pub/e3sm/archive/1_1_ECA/BGC-v1/20190308.CNTL.1850-2014

and for the lines contained within, they are excluded if they begin with any of the "disqualifying" prefix values

    [ 'rest/', 'post/', 'test', 'init', 'run/try', 'run/bench', 'old/run', 'pp/remap', 'a-prime', 'lnd_rerun', 'atm/ncdiff', 'archive/rest', 'fullD', 'photic']

those that remain are sorted and the first and last are output to the file, prefixed with "HEADF,"  and "HEADL,", respectively.

The process then exits, and the user must manually determine if the first and last matching filenames appear to come from the same dataset, and the correct dataset.

For instance, if the output file contained a section like

    DECK,1_0,abrupt-4xCO2,ens1,lnd_nat_mon,/p/user_pub/e3sm/archive/1_1_ECA/BGC-v1/20190308.CNTL.1850-2014
        HEADF,archive/lnd/hist/20180215.DECKv1b_abrupt4xCO2.ne30_oEC.edison.clm2.h0.0001-01.nc
        HEADL,archive/lnd/hist/20180215.DECKv1b_abrupt4xCO2.ne30_oEC.edison.clm2.h0.0156-10.nc
        HEADF,run/20180215.DECKv1b_abrupt4xCO2.ne30_oEC.edison.clm2.h0.0155-12.nc
        HEADL,run/20180215.DECKv1b_abrupt4xCO2.ne30_oEC.edison.clm2.h0.0155-12.nc

and it is determined that the first pair of (HEADF,HEADL) lines are from the correct dataset, select everything after the "HEADF" (including the comma) ands
append that to the section header line, and then "wildcard" the variant portion of the pattern (the "0001-01" simdata portion), resulting in the finished line

    DECK,1_0,abrupt-4xCO2,ens1,lnd_nat_mon,/p/user_pub/e3sm/archive/1_1_ECA/BGC-v1/20190308.CNTL.1850-2014,archive/lnd/hist/20180215.DECKv1b_abrupt4xCO2.ne30_oEC.edison.clm2.h0.*.nc

Once this has been dome for every section, save the file and eliminate all "HEADF" and "HEADL" lines by using "grep -v HEAD" on the file.

The remaining lines represent the update to the Archive_Map necessary to accommodate the new archive(s) and their automated extraction.


NOTE:  All of the above could be conducted entirely in-memory, and not involve the product of the "per-pattern" name-list files.  But I have found that it can bes
 very useful to have them output, for when "first and last" seem wrong, one can usually identify the problem by manually scrolling through the list of matched filenames.


PREREQS:

	Ensure that archive/.cfg file "Standard_Datatype_Extraction_Patterns" are complete with respect to required publications


The Working Process:

0.  Upon arrival of new Archives, ensure that /p/user_pub/e3sm/archive/.cfg/Archive_Locator is updated.


EXTRA_CREDIT:

4.  Ensure the file "/p/user_pub/e3sm/archive/.cfg/Filename_SimDate_Locator" has an entry
    for each experiment dataset, indicating the "dot"-delimited position of the sim-date
    value in each filename.  Use the file "headset12_lists_first_last" to obtain the information.


