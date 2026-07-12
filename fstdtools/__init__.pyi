
def convert(input_path: str, output_path: str, compress_level: int, compress_dict_size: int, block_size: int, thread=0, substyle=False, passcode=None) -> int:
    """Convert mdx/mdd file to fstdx/fstdd file.
    Args:
        input_path (str): mdx/mdd file path.
        output_path (str): fstdx/fstdd file path.
        compress_level (int): Compress level. 0-22.
        compress_dict_size (int): Compress dict size. 1-130, unit: KB.
        block_size (int): Block size. 4-512, unit: KB.
        thread (int, optional): Thread count. Defaults to 0, auto detect.
        substyle (bool, optional): Whether to use substyle. Defaults to False.
        passcode (str, optional): Passcode for mdx/mdd file. Defaults to None.

    Returns:
        int: 0 if success, otherwise error code.
    """
    ...
