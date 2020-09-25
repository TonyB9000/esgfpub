
  These configuration files are "live" in the directory

	/p/user_pub/e3sm/archive/.cfg/

  and assist in the location and extraction of datasets from the E3SM archives.

PREFACE:

	It is unfortunate that a given dataset from a single experiment and ensemble may be spread across
	not only multiple archives, but even under multiple tar-paths within an archive, due to runs that 
	were "broken" by year-range, and consequently by the machine upon which a run was conducted.

	One must therefore be prepared to process multiple lines and paths, even for a single dataset.

	The inconsistencies in archive names and tar-paths, even for otherwise identically-names files
	across the span of campaigns and authors necessitates the files included herein for automation.


Archive_Locator:

	The "Archive_Locator" provides the full-path to the archive that contains the materials for a
	given campaign or model, experiment, and ensemble if appropriate.  For Example:

		archive_path=`cat Archive_Locator | grep 1_0 | grep F2010-HR | cut -f5 -d,`

	will set archive_path to

		/p/user_pub/e3sm/archive/1_0/HR-v1/cori-knl.20190214_maint-1.0.F2010-CMIP6-HR.dailySST.noCNT.ne120_oRRS18v3


Standard_Dataset_Extraction_Patterns:

	This file gives the wild-card patterns that isolate dataset filenames according to Dataset Type.
	The contents are:

		atm nat mon,*cam.h0*,DEFAULT,
		atm nat day,*cam.h1*,DEFAULT,
		atm nat 6hr_snap,*cam.h2*,DEFAULT,
		atm nat 6hr,*cam.h3*,DEFAULT,
		atm nat 3hr,*cam.h4*,DEFAULT,
		atm nat day_cosp,*cam.h5*,DEFAULT,
		lnd nat mon,*clm2.h0*,DEFAULT,
		river nat mon,*mosart.h0*,DEFAULT,
		ocn nat mon,*mpaso.hist.am.timeSeriesStatsMonthly.*,DEFAULT,
		ocn nat 5day,*mpaso.hist.am.highFrequencyOutput.*,DEFAULT,
		sea-ice nat mon,*mpascice.hist.am.timeSeriesStatsMonthly.*,DEFAULT,
		sea-ice nat day,*mpascice.hist.am.timeSeriesStatsDaily.*,DEFAULT,

	NOTE: These patterns alone are INSUFFICIENT to isolate the desired dataset files from a given archive, 
	because different archives place the same files under multiple and varied tar-paths. That is, a given
	dataset filename may appear multiple times in an archive under the tar paths

		run/filename
		rest/filename
		archive/atm/hist/filename

	and across archives from different authors or campaigns, these paths may appear as

		archive/atm/hist/filename  (in one archive)
		atm/hist/filename  (in a different archive)

	These and other variabilities are addressed with the following Archive_Map.


Archive_Map:

	The "Archive_Map" expands upon both the above Archive_Locator and "Standard_Dataset_Extraction_Patterns" files,
	beginning with a cross-product. This augments each experiment search key with a dataset type-code, giving

		Campaign,Model,Experiment,Ensemble,realm_grid_freq

	as the searchable "keys", and then augmenting the archive path with the "standard-filetype" search pattern.

	Then, MANUALLY, each line was refined to prepend the final search-pattern with the campaign/author-specific
	tar-path(s) that finally isolate only the dataset files intended for publication or related analysis.

	The related file, "Archive_Map_headers" gives the precise fieldnames and positions in the Archive_Map, namely

		Campaign,Model,Experiment,Ensemble,DatasetType,ArchivePath,DatatypeTarExtractionPattern,Notes

	Armed with this file, one can set up a "holodeck" of sym-links to an identified archive, and then issue

		zstash [ls|extract] --hpss=none DatatypeTarExtractionPattern(s)

	in order to list or extract desired dataset files.


