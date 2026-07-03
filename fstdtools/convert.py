import os.path
import fstd
import json
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm

from .mdict.readmdict import MDX, MDD


def get_meta(source, substyle=False, passcode=None):
    meta = {}
    if source.endswith('.mdx'):
        encoding = ''
        md = MDX(source, encoding, substyle, passcode)
    if source.endswith('.mdd'):
        md = MDD(source, passcode)

    for key, value in md.header.items():
        # key has been decode from UTF-16 and encode again with UTF-8
        key = key.decode('UTF-8').lower().title()
        value = value.decode('UTF-8')
        meta[key] = value
        if value == 'Yes':
            meta[key] = True
        elif value == 'No':
            meta[key] = False

    return meta


def convert(source, target, compress_level, compress_dict_size, block_size, thread=0, substyle=False, passcode=None):
    meta_info = get_meta(source, substyle, passcode)
    meta_json_str = json.dumps(meta_info, ensure_ascii=False)
    if source.endswith('.mdx'):
        encoding = ''
        mdx = MDX(source, encoding, substyle, passcode)
        item_count = 0
        keys = []
        values = []

        print("Extracting raw data from mdx:")
        bar = tqdm(total=len(mdx), unit='rec')
        for key, value in mdx.items():
            if not value.strip():
                bar.write('Skip entry: %s' % key)
                continue
            item_count += 1
            keys.append(key)
            values.append(value)
            bar.update(1)
        bar.close()
        writer = fstd.FstdxWriter()
        writer.compile_fstdx(target, keys, values, meta_json_str, block_size, compress_level, compress_dict_size, thread, False, True)
    elif source.endswith('.mdd'):
        mdd = MDD(source, passcode)
        writer = fstd.FstddWriter()
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            writer.compile_fstdd,
            len(mdd),
            target,
            meta_json_str,
            block_size,
            compress_level,
            thread,
            False
        )
        for key, value in mdd.items():
            fname = key.decode('UTF-8').replace('\\', os.path.sep)
            if not writer.push_file_stream(fname, value):
                break
        ret = future.result()
        if ret != 0:
            print("Compile fstdd failed with error code: %d" % ret)
    else:
        raise ValueError("Unsupported source file type: %s" % source)
