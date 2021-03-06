import warnings
warnings.simplefilter('ignore')

from esgfpub.util import path_to_dataset_id, print_message
from dask.distributed import get_client, worker_client, as_completed
from dask.diagnostics import ProgressBar
# import vcs
import xarray as xr
import numpy as np
from datetime import datetime
import os
from tqdm import tqdm

from matplotlib import pyplot as plt


import logging
logger = logging.getLogger("distributed.worker")
logger.setLevel(logging.ERROR)


def plot_minmaxmean(outpath, ds, vmax, dataset_id, debug=False):

    fig, ax1 = plt.subplots()
    fig.set_size_inches(18.5, 10.5)
    plt.title(dataset_id)
    
    xtick_positions = [i for i, t in enumerate(ds['time']) if i % (120) == 0]
    xtick_values = [t.values.item().strftime('%Y') for i, t in enumerate(ds['time']) if i % (120) == 0]
    plt.xticks(xtick_positions, xtick_values)


    ax1.set_xlabel('year')
    var = next(filter(lambda x: 'bnds' not in x, ds.data_vars))
    ax1.set_ylabel(ds[var].units)

    ax1.plot(ds['means'], color='tab:blue')

    ax2 = ax1.twinx()
    ax2.plot(vmax, color='tab:red')

    plt.savefig(outpath, dpi=100)
    return


def run_chunk(ds, dataset_id, maxrollingvar, maxrollingstd, segment, index):
    issues = list()
    vmax = np.ndarray(shape=(len(ds['time'])))
    idx = -1
    for step in ds['time']:
        idx += 1

        mean = ds.sel(time=step)['means'].values
        if not isinstance(mean, int) and not isinstance(mean, float) and mean.size > 1:
            mean = max(mean)

        if mean == 0.0:
            issues.append(
                f"\tZero data issue found for {dataset_id} at {str(step['time'].item())[:7]}")
            vmax[idx] = 0
            continue

        max_rolling_var = maxrollingvar.sel(time=step)
        mx_rolling_std = maxrollingstd.sel(time=step)
        # if there's a NAN in the array skip it
        if np.isnan(max_rolling_var) or np.isnan(mx_rolling_std) or np.isnan(mean):
            vmax[idx] = 0
            continue
        if not mx_rolling_std.any():
            vmax[idx] = 0
            continue

        # import ipdb; ipdb.set_trace()
        max_variance = pow((mean - max_rolling_var)/mx_rolling_std, 2).values.item()
        vmax[idx] = max_variance
        

    # if the variance is greater then 3x the variance std mark it as an issue
    threshold = 3 * vmax.std() + vmax.mean()
    for idx, v in enumerate(vmax):
        if v >= threshold:
            issues.append(
                f"\tmax variance issue found for {dataset_id} at {str( ds['time'][idx].item() )[:7]}")
    return vmax, issues, segment, threshold

def check_sq_variance(dataset_path, dataset_id, variable, pngpath, pbar, debug=False):
    issues = []
    client = get_client()
    num_segments = 10
    pbar.total = num_segments + 2
    if pbar.n != 0:
        pbar.n = 0
        pbar.last_print_n = 0
        pbar.update()

    with xr.open_mfdataset(dataset_path + '/*.nc') as ds:

        segments = list(
            range(0, ds['time'].size, ds['time'].size//num_segments))
        vmax = np.zeros(ds['time'].size)
        futures = []
        
        if 'time' not in ds.coords:
            return [], dataset_id
        
        dims = list()
        possible_dims = ['depth', 'lat', 'lon', 'plev', 'tau', 'lev', 'sector']
        for i in possible_dims:
            if i in ds.dims:
                if i == 'sector':
                    dims.append('basin')
                else:
                    dims.append(i)
        
        dims = tuple(dims)
        if 'lat' not in dims and 'lon' not in dims:
            ds['means'] = ds[variable]
            # maxrollingstd = client.compute( ds['means'].std ).result()
            # maxrollingvar = client.compute( ds['means'].mean ).result()
        else:
            ds['means'] = client.compute( ds[variable].mean(dim=dims) ).result()
            # maxrollingstd = ds['means'].std().compute()
            # maxrollingvar = ds['means'].mean().compute()
            # maxrollingstd = client.compute( ds['means'].std ).result()
            # maxrollingvar = client.compute( ds['means'].mean ).result()
        # import ipdb; ipdb.set_trace()
        ds['means'] = ds['means'][~np.isnan(ds['means'])]
        pbar.update(1)
           
        maxrollingvar = client.compute( ds['means'].rolling({'time':120}, min_periods=1).mean() )
        maxrollingstd = client.compute( ds['means'].rolling({'time':120}, min_periods=1).std() )
        for idx, seg in enumerate(segments):
            if idx == num_segments - 1:
                seg_end = ds['time'].size
            else:
                seg_end = segments[idx + 1]

            temp_ds = ds['time'][seg: seg_end]
            chunk = ds.sel(time=temp_ds)
            futures.append(
                client.submit(
                    run_chunk, 
                        chunk, 
                        dataset_id, 
                        maxrollingvar, 
                        maxrollingstd, 
                        (seg, seg_end), 
                        idx))

        for f in as_completed(futures):
            pbar.update(1)
            vx, issues, seg, threshold = f.result()
            vmax[seg[0]: seg[1]] = vx
        plot_minmaxmean(pngpath, ds, vmax, dataset_id, debug=debug)

    return issues


def verify_dataset(dataset_path, dataset_id, variable, output, pbar, debug=False):

    issues = list()
    if not os.path.exists(output):
        os.makedirs(output)

    pngpath = os.path.join(output, f"{dataset_id}.png")
    return check_sq_variance(dataset_path, dataset_id, variable, pngpath, pbar, debug)
