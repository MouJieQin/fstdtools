import click
import fstd
import json
from pathlib import Path
from .convert import convert as converter
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
@click.argument("source_file", type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.argument("output_path", type=click.Path(file_okay=True, dir_okay=True, writable=True), required=False)
@click.option("-k", "--key-path", type=str, required=False, help="key path only for fstdd, e.g. 'folder1/folder2/file.png'")
@click.option("-y", "--yes", is_flag=True, help="overwrite output file, no confirm")
@click.pass_context
def extract(ctx, source_file, output_path, key_path, yes):
    src = Path(source_file)
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
@click.option("--compress-dict-size", type=click.IntRange(min=1, max=130), default=100, help="compression dict size, only for fstdx, 1~130.", show_default=True)
@click.option("-b", "--block-size", type=click.IntRange(min=4, max=512), default=4, help="block size, unit: KB.", show_default=True)
@click.option("-t", "--thread", type=int, default=0, help="concurrency thread count, auto detect cpu count if 0.", show_default=True)
@click.option("--substyle/--no-substyle", default=False, help="enable substyle, only for mdx/mdd to fstdx/fstdd.", show_default=True)
@click.option("-y", "--yes", is_flag=True, help="overwrite output file, no confirm")
@click.pass_context
def convert_(
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
        writer.compile_fstdd(source_file, output_file, json.dumps(meta), block_size, compress_level, thread, verbose >= 1)

    elif src.suffix == ".mdx":
        if out and not out.suffix == ".fstdx":
            click.echo(click.style("For mdx source, output file must have .fstdx extension", fg="red"), err=True)
            ctx.exit(code=1)
        if not output_file:
            output_file = str(src.with_suffix(".fstdx"))
            overwrite_confirm(ctx, output_file, yes)
        show_verbose()
        converter(source_file, output_file, compress_level, compress_dict_size, block_size, thread, substyle, None)

    elif src.suffix == ".mdd":
        if out and not out.suffix == ".fstdd":
            click.echo(click.style("For mdd source, output file must have .fstdd extension", fg="red"), err=True)
            ctx.exit(code=1)
        if not output_file:
            output_file = str(src.with_suffix(".fstdd"))
            overwrite_confirm(ctx, output_file, yes)
        show_verbose()
        converter(source_file, output_file, compress_level, compress_dict_size, block_size, thread, substyle, None)

    else:
        # see src as txt or fstdx, then convert to fstdx
        if out and not out.suffix == ".fstdx":
            click.echo(click.style("For txt or fstdx source, output file must have .fstdx extension", fg="red"), err=True)
            ctx.exit(code=1)
        if not output_file:
            output_file = str(src.with_suffix(".fstdx"))
            overwrite_confirm(ctx, output_file, yes)
        writer = fstd.FstdxWriter()
        show_verbose()
        writer.compile_fstdx(source_file, output_file, json.dumps(meta), block_size, compress_level, compress_dict_size, thread, False, verbose >= 1)

    click.echo(click.style(f"{output_file} written successfully", fg="bright_green"))
    ctx.exit(code=0)


if __name__ == "__main__":
    cli()
