from os.path import realpath
from typing import List

import click
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import get_module_reader, get_codes
from starkware.cairo.lang.compiler.constants import MAIN_SCOPE
from starkware.cairo.lang.compiler.preprocessor.preprocess_codes import preprocess_codes
from starkware.starknet.compiler.starknet_pass_manager import starknet_pass_manager


def ddd(files: List[str], cairo_path: List[str]):
    cairo_path = [realpath(path) for path in cairo_path]
    module_reader = get_module_reader(cairo_path=cairo_path)
    pass_manager = starknet_pass_manager(prime=DEFAULT_PRIME, read_module=module_reader.read)
    preprocess_codes(codes=get_codes(files), pass_manager=pass_manager, main_scope=MAIN_SCOPE)

    return [
        file
        for file in module_reader.source_files
        if [path for path in cairo_path if file.startswith(path)]
    ]


@click.command()
@click.option('--cairo_path', multiple=True)
@click.argument('files', nargs=-1, required=True)
def cli(files: List[str], cairo_path: List[str]):
    for file in ddd(files, cairo_path):
        print(file)
