import click
import fstd
import json
from pathlib import Path
from .convert import convert
from importlib.metadata import version, PackageNotFoundError


def get_version():
    try:
        return version("fstdtools")
    except PackageNotFoundError:
        return "0.0.0-unknown"


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    ver = fstd.get_version()
    click.echo(click.style(f"fstdtools v{get_version()} | fstd core v{ver}", fg="green"))
    ctx.exit()


def overwrite_confirm(ctx, file_path, yes):
    if not yes and Path(file_path).exists():
        if not click.confirm(click.style(f"File {file_path} already exists. Overwrite?", fg="yellow"), default=False):
            click.echo("Operation cancelled", err=True)
            ctx.exit(code=1)
            return False


def print_search_result(ctx, res):
    for item in res:
        print(item)
    ctx.exit(code=0)


# ===================== Global options =====================
@click.group(name="fstdtools", help="CLI tools for fstd dictionary to pack/unpack/list/info/convert.", context_settings={"help_option_names": ["-h", "--help"]})
@click.option("-V", "--version", is_flag=True, callback=print_version, expose_value=False, is_eager=True, help="print version info and exit")
@click.option("--verbose", "-v", count=True, help="log level, -v simple log, -vv debug log")
@click.option("--log-level", "-l", type=click.IntRange(min=0, max=6), default=4, show_default=True, envvar="FSTDTOOLS_LOG_LEVEL", help=" log_level: 0-6, 0 is trace, 1 is debug, 2 is info, 3 is warn, 4 is error, 5 is critical, 6 is off")
@click.pass_context
def cli(ctx, verbose, log_level):
    """global init, all subcommands share this context"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["log_level"] = log_level
    fstd.set_log_level(log_level)


# ===================== Subcommands extract =====================
@cli.command(name="extract", help="extract raw data from fstdx/fstdd")
@click.argument("fstd_file", type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.argument("output_path", type=click.Path(file_okay=True, dir_okay=True, writable=True), required=False)
@click.option("-k", "--key-path", type=str, required=False, help="key path only for fstdd, e.g. 'folder1/folder2/file.png'")
@click.option("-y", "--yes", is_flag=True, help="overwrite output file, no confirm")
@click.pass_context
def extract(ctx, fstd_file, output_path, key_path, yes):
    src = Path(fstd_file)
    out = Path(output_path) if output_path else None

    if out and out.exists() and not yes:
        if not click.confirm(click.style(f"File {out} already exists, overwrite?", fg="yellow")):
            click.echo("Operation cancelled", err=True)
            ctx.exit(code=1)

    if src.suffix == ".fstdx":
        if not output_path:
            output_path = str(src.with_suffix(".txt"))
            overwrite_confirm(ctx, output_path, yes)
        reader = fstd.FstdxReader(str(src.resolve()))
        if not reader.is_valid():
            click.echo(click.style(f"Invalid fstdx file {src}", fg="red"), err=True)
            ctx.exit(code=1)
        if reader.extract(output_path):
            click.echo(click.style(f"{str(Path(output_path).resolve())} extracted successfully", fg="bright_green"))
        else:
            ctx.exit(code=1)
    elif src.suffix == ".fstdd":
        if not output_path:
            output_path = str(src.parent / "data")
            overwrite_confirm(ctx, output_path, yes)
        reader = fstd.FstddReader(str(src.resolve()))
        if not reader.is_valid():
            click.echo(click.style(f"Invalid fstdd file {src}", fg="red"), err=True)
            ctx.exit(code=1)
        if key_path:
            if reader.extract(key_path, output_path):
                click.echo(click.style(f"{str(Path(output_path)/key_path)} extracted successfully", fg="bright_green"))
            else:
                ctx.exit(code=1)
        else:
            if reader.extract_all(output_path):
                click.echo(click.style(f"{str(Path(output_path).resolve())} extracted successfully", fg="bright_green"))
            else:
                ctx.exit(code=1)
    else:
        click.echo(click.style(f"Invalid file type {src.suffix}", fg="red"), err=True)
        ctx.exit(code=1)
    ctx.exit(code=0)


# ===================== Subcommands write =====================
@cli.command(name="write", help="Compile from txt/fstdx/mdx to fstdx, from directory/mdd to fstdd")
@click.argument("source_file", type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True))
@click.argument("output_file", type=click.Path(file_okay=True, dir_okay=False, writable=True), required=False)
@click.option("-T", "--title", type=str, required=False, help="title text/file of the dictionary")
@click.option("-D", "--description", type=str, required=False, help="description text/file of the dictionary")
@click.option("-e", "--encoding", type=str, required=False, default="utf-8", help="encoding of the dictionary.", show_default=True)
@click.option("-m", "--meta", type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True), required=False, help="meta file(json) of the dictionary")
@click.option("-c", "--compress-level", type=click.IntRange(min=0, max=22), default=5, help="compression level 0(fast) ~ 22(max compress).", show_default=True)
@click.option("-d", "--compress-dict-size", type=click.IntRange(min=1, max=130), default=100, help="compression dict size, only for fstdx, 1~130.", show_default=True)
@click.option("-b", "--block-size", type=click.IntRange(min=4, max=512), default=4, help="block size, unit: KB.", show_default=True)
@click.option("-t", "--thread", type=int, default=0, help="concurrency thread count, auto detect cpu count if 0.", show_default=True)
@click.option("--substyle/--no-substyle", default=False, help="enable substyle, only for mdx/mdd to fstdx/fstdd.", show_default=True)
@click.option("-y", "--yes", is_flag=True, help="overwrite output file, no confirm")
@click.pass_context
def write(
    ctx, source_file, output_file, title, description, encoding, meta, compress_level, compress_dict_size, block_size, thread, substyle, yes
):
    verbose = ctx.obj["verbose"]
    src = Path(source_file)
    out = Path(output_file) if output_file else None

    if not src.exists():
        click.echo(click.style(f"Source file {src} does not exist", fg="red"), err=True)
        ctx.exit(code=1)

    if out and out.exists() and not yes:
        if not click.confirm(click.style(f"File {out} already exists, overwrite?", fg="yellow")):
            click.echo("Operation cancelled", err=True)
            ctx.exit(code=1)

    if not meta:
        meta = {}
    else:
        if not Path(meta).is_file():
            click.echo(click.style(f"Meta file {meta} does not exist", fg="red"), err=True)
            ctx.exit(code=1)
        else:
            try:
                meta = json.load(open(meta, 'rt', encoding='utf-8'))
            except json.JSONDecodeError:
                click.echo(click.style(f"Meta file {meta} is not valid json", fg="red"), err=True)
                ctx.exit(code=1)
            except Exception as e:
                click.echo(click.style(f"Meta file {meta} error: {e}", fg="red"), err=True)
                ctx.exit(code=1)

    if title:
        if Path(title).is_file():
            title = open(title, 'rt', encoding='utf-8').read().strip()
        meta["Title"] = title

    if description:
        if Path(description).is_file():
            description = open(description, 'rt', encoding='utf-8').read().strip()
        meta["Description"] = description

    if encoding:
        encoding = encoding.upper()
        meta["Encoding"] = encoding

    def show_verbose():
        if verbose >= 1:
            click.echo(click.style(f"Source file: {src}", fg="cyan"))
            click.echo(click.style(f"Output file: {output_file if output_file else 'default'}", fg="cyan"))
            click.echo(click.style(f"Compression level: {compress_level}", fg="cyan"))
            click.echo(click.style(f"Compression dict size: {compress_dict_size}", fg="cyan"))
            click.echo(click.style(f"Block size: {block_size}", fg="cyan"))
            click.echo(click.style(f"Concurrency threads: {thread if thread > 0 else 'auto detect cpu count'}", fg="cyan"))
            click.echo(click.style(f"Meta: {json.dumps(meta, ensure_ascii=False,indent=2) if meta else 'use default'}", fg="cyan"))

    if src.is_dir():
        if out and not out.suffix == ".fstdd":
            click.echo(click.style("For mdd source, output file must have .fstdd extension", fg="red"), err=True)
            ctx.exit(code=1)
        if not output_file:
            output_file = str(src.with_suffix(".fstdd"))
            overwrite_confirm(ctx, output_file, yes)
        writer = fstd.FstddWriter()
        show_verbose()
        ret = writer.compile_fstdd(source_file, output_file, json.dumps(meta), block_size, compress_level, thread, verbose >= 1)
        if ret != 0:
            ctx.exit(code=ret)
    elif src.suffix == ".mdx":
        if out and not out.suffix == ".fstdx":
            click.echo(click.style("For mdx source, output file must have .fstdx extension", fg="red"), err=True)
            ctx.exit(code=1)
        if not output_file:
            output_file = str(src.with_suffix(".fstdx"))
            overwrite_confirm(ctx, output_file, yes)
        show_verbose()
        ret = convert(source_file, output_file, compress_level, compress_dict_size, block_size, thread, substyle, None)
        if ret != 0:
            ctx.exit(code=ret)
    elif src.suffix == ".mdd":
        if out and not out.suffix == ".fstdd":
            click.echo(click.style("For mdd source, output file must have .fstdd extension", fg="red"), err=True)
            ctx.exit(code=1)
        if not output_file:
            output_file = str(src.with_suffix(".fstdd"))
            overwrite_confirm(ctx, output_file, yes)
        show_verbose()
        ret = convert(source_file, output_file, compress_level, compress_dict_size, block_size, thread, substyle, None)
        if ret != 0:
            ctx.exit(code=ret)
    else:
        # see src as txt or fstdx, then convert to fstdx
        if out and out.suffix != ".fstdx":
            click.echo(click.style("For txt or fstdx source, output file must have .fstdx extension", fg="red"), err=True)
            ctx.exit(code=1)
        if not output_file:
            if src.suffix == ".fstdx":
                output_file = str(src.resolve()) + ".fstdx"
            else:
                output_file = str(src.with_suffix(".fstdx"))
            overwrite_confirm(ctx, output_file, yes)
        if str(src.resolve()) == str(Path(output_file).resolve()):
            click.echo(click.style("Output file is same as source file, no conversion", fg="red"), err=True)
            ctx.exit(code=1)
        writer = fstd.FstdxWriter()
        show_verbose()
        ret = writer.compile_fstdx(source_file, output_file, json.dumps(meta), block_size, compress_level, compress_dict_size, thread, False, verbose >= 1)
        if ret != 0:
            ctx.exit(code=ret)
    click.echo(click.style(f"{output_file} written successfully", fg="bright_green"))
    ctx.exit(code=0)


# ===================== Subcommands search =====================
@cli.command(name="search", help="Search in fstdx/fstdd dictionary")
@click.argument("fstd_file", required=False, type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True))
@click.option("-m", "--meta", is_flag=True, required=False, help="show meta information")
@click.option("-H", "--header", is_flag=True, required=False, help="show header information")
@click.option("-u", "--enumerate", is_flag=True, required=False, help="enumerate all keys in dictionary")
@click.option("-c", "--contains", type=str, required=False, help="check if key exists in dictionary")
@click.option("-k", "--key", type=str, required=False, help="show the value of key. (exact match)")
@click.option("-p", "--predictive", type=str, required=False, help="perform predictive search")
@click.option("-r", "--regex", type=str, required=False, help="Run regex pattern search")
@click.option("-s", "--spellcheck", type=str, required=False, help="Spell-check a word")
@click.option("-g", "--suggest", type=str, required=False, help="Get word suggestions for")
@click.option("-C", "--common-prefix", type=str, required=False, help="Search common prefix matches")
@click.option("-l", "--longest-prefix", type=str, required=False, help="Find longest common prefix")
@click.option("-e", "--edit-distance", type=int, required=False, help="Max edit distance for fuzzy search")
@click.option("-P", "--prefix-distance", type=int, required=False, help="Max distance for prefix distance search")
@click.option("-x", "--prior-suffix", type=str, multiple=True, required=False, help="Prior suffix only for prefix distance search")
@click.option("-f", "--dictionary", multiple=True, type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True), required=False, help="Add multiple .fstdx files for batch search")
@click.option("-t", "--thread", type=int, default=0, help="concurrency thread count, auto detect cpu count if 0.", show_default=True)
@click.pass_context
def search(ctx, fstd_file, meta, header, contains, key, predictive,
           enumerate, regex, spellcheck, suggest, common_prefix, longest_prefix, edit_distance, prefix_distance, prior_suffix, dictionary, thread):
    """
    Search in fstdx/fstdd dictionary.
    """
    if dictionary:
        searcher = fstd.FstdxSearcher(thread)
        if not searcher.is_valid():
            click.echo(click.style("Invalid thread count. Please use -t to specify a valid thread count.", fg="red"), err=True)
            ctx.exit(code=1)
        for dict_file in dictionary:
            if not searcher.insert(dict_file, dict_file):
                click.echo(click.style(f"Insert fstdx file {dict_file} failed.", fg="red"), err=True)
                ctx.exit(code=1)
        if contains:
            click.echo(click.style(f"{searcher.contains(contains, dictionary)}", fg="cyan"))
            ctx.exit(code=0)
        if predictive:
            print_search_result(ctx, searcher.predictive_search(predictive, dictionary))
        if regex:
            res = searcher.regex_search(regex, dictionary)
            if res[1]:
                click.echo(click.style(f"Regex error: {res[1]}", fg="red"), err=True)
                ctx.exit(code=1)
            print_search_result(ctx, res[0])
        if suggest:
            print_search_result(ctx, searcher.suggest(suggest, dictionary))
        if common_prefix:
            print_search_result(ctx, searcher.common_prefix_search(common_prefix, dictionary))
        if longest_prefix:
            print(longest_prefix[0:searcher.longest_prefix_len(longest_prefix, dictionary)])
            ctx.exit(code=0)
        if edit_distance:
            if not key:
                click.echo(click.style("Please use -k to specify a key.", fg="red"), err=True)
                ctx.exit(code=1)
            print_search_result(ctx, searcher.edit_distance_search(key, dictionary, edit_distance))
        if prefix_distance:
            if not key:
                click.echo(click.style("Please use -k to specify a key.", fg="red"), err=True)
                ctx.exit(code=1)
            if prior_suffix:
                searcher.insert_prior_suffix(prior_suffix)
            print_search_result(ctx, searcher.prefix_distance_search(key, dictionary, prefix_distance))
        if key:
            res = searcher.exact_match_search(key, dictionary)
            if not res:
                click.echo(click.style(f"Key {key} not found in dictionaries.", fg="red"), err=True)
                ctx.exit(code=1)
            else:
                for name, values in res.items():
                    click.echo(click.style(f"# {name}:", fg="cyan"))
                    click.echo(click.style("---", fg="cyan"))
                    for value in values:
                        print(value)
                        click.echo(click.style("---", fg="cyan"))
                ctx.exit(code=0)
        click.echo(click.style("Invalid option to search in multiple fstdx files.", fg="red"), err=True)
        ctx.exit(code=1)
    if not fstd_file:
        click.echo(click.style("Please specify a fstdx/fstdd file.", fg="red"), err=True)
        ctx.exit(code=1)
    src = Path(fstd_file)
    if (src.suffix == ".fstdd"):
        reader = fstd.FstddReader(fstd_file)
        if not reader.is_valid():
            click.echo(click.style(f"Invalid fstdd file {fstd_file}", fg="red"), err=True)
            ctx.exit(code=1)
        if meta:
            click.echo(click.style(f"{json.dumps(json.loads(reader.get_meta()), ensure_ascii=False,indent=2)}", fg="cyan"))
            ctx.exit(code=0)
        if header:
            click.echo(click.style(f"{json.dumps(json.loads(reader.get_header()), ensure_ascii=False,indent=2)}", fg="cyan"))
            ctx.exit(code=0)
        if contains:
            click.echo(click.style(f"{reader.contains(contains)}", fg="cyan"))
            ctx.exit(code=0)
        if enumerate:
            all_keys = reader.extract_all_key()
            for key in all_keys:
                print(key)
            ctx.exit(code=0)
        click.echo(click.style("Invalid option to search in fstdd file.", fg="red"), err=True)
        ctx.exit(code=1)
    elif (src.suffix == ".fstdx"):
        reader = fstd.FstdxReader(fstd_file)
        if not reader.is_valid():
            click.echo(click.style(f"Invalid fstdx file {fstd_file}", fg="red"), err=True)
            ctx.exit(code=1)
        if meta:
            click.echo(click.style(f"{json.dumps(json.loads(reader.get_meta()), ensure_ascii=False,indent=2)}", fg="cyan"))
            ctx.exit(code=0)
        if header:
            click.echo(click.style(f"{json.dumps(json.loads(reader.get_header()), ensure_ascii=False,indent=2)}", fg="cyan"))
            ctx.exit(code=0)
        if contains:
            click.echo(click.style(f"{reader.contains(contains)}", fg="cyan"))
            ctx.exit(code=0)
        if enumerate:
            reader.enumerate_print()
            ctx.exit(code=0)
        if predictive:
            print_search_result(ctx, reader.predictive_search(predictive))
        if regex:
            res = reader.regex_search(regex, thread)
            if res[1]:
                click.echo(click.style(f"Regex error: {res[1]}", fg="red"), err=True)
                ctx.exit(code=1)
            print_search_result(ctx, res[0])
        if spellcheck:
            print_search_result(ctx, reader.spellcheck_word(spellcheck, dictionary))
        if suggest:
            print_search_result(ctx, reader.suggest(suggest))
        if common_prefix:
            print_search_result(ctx, reader.common_prefix_search(common_prefix))
        if longest_prefix:
            print(longest_prefix[0:reader.longest_prefix_len(longest_prefix)])
            ctx.exit(code=0)
        if edit_distance:
            if not key:
                click.echo(click.style("Please use -k to specify a key.", fg="red"), err=True)
                ctx.exit(code=1)
            print_search_result(ctx, reader.edit_distance_search(key, edit_distance))
        if key:
            res = reader.exact_match_search(key)
            if res:
                print_search_result(ctx, res)
            else:
                click.echo(click.style(f"Key {key} not found in dictionary.", fg="red"), err=True)
                ctx.exit(code=1)
        if prefix_distance:
            click.echo(click.style("Prefix distance search not implemented to search in single fstdx. Use -f to search instead.", fg="red"), err=True)
            ctx.exit(code=1)
        click.echo(click.style("Invalid option to search in fstdx file.", fg="red"), err=True)
        ctx.exit(code=1)
    else:
        click.echo(click.style(f"Invalid file type {src.suffix}", fg="red"), err=True)
        ctx.exit(code=1)


if __name__ == "__main__":
    cli()
