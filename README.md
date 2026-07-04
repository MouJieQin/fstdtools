# fstdtools
A command line tool to pack/unpack/list/info [fstd](https://github.com/MouJieQin/fstd) dictionary and convert mdx/mdd to fstdx/fstdd.

## Install

```
pip install fstdtools
```

## Usage

### Compile

Convert mdx/mdd to fstdx/fstdd

```
fstdtools write dict.mdx
fstdtools write dict.mdd
```

Compile a raw txt file to fstdx

```
fstdtools write dict.txt
```

> 1. The first entry requires no preceding delimiter: write the entry word (key) directly, followed by its corresponding definition (value). Definitions can span multiple lines, but entry words must stay on a single line.
> 2. Starting from the second entry, each entry word (key) must be preceded by the delimiter `</>`. Entry words must still be written on one line, while definitions can span multiple lines.
> 3. The end of each complete entry (entry word + corresponding definition) must be marked with the delimiter `</>` as a closing tag.


````
Ab
The definition of Ab
</>
Ababdeh
The definition of Ababdeh
</>
Abby
The definition of Abby
</>
...
````

Compile a directory  to fstdd

```
# data is a directory
fstdtools write data dict.mdd
```

It's supported to compile a fstdx from a  fstdx file,  but not supported for fstdd now.

```
fstdtools -v write -b 8 -c 15 -d 130 -T "dict titile" -D "dict description" dict.fstdx dict.15-8-130.fstdx
```

### Extract

Extract raw text from a fstdx

```
fstdtools extract dict.fstdx
```

Extract all files from a fstdd

```
fstdtools extract dict.fstdd
```

Extract a single file from a fstdd by key path

```
fstdtools extract -k path/to/1.png dict.fstdd
```

### Search

Show the meta information of fstdx/fstdd

```
fstdtools search -m dict.fstdx
fstdtools search -m dict.fstdd
```

All key list of fstdx/fstdd

```
fstdtools search -u dict.fstdx
fstdtools search -u dict.fstdd
```

Query the value of a key from fstdx

```
fstdtools search -k dictionary dict.fstdx
```

Search a regex pattern

```
fstdtools search -r 'd.*i.*on.*y$' dict.fstdx
```

Spell-check a word

```
fstdtools search -s 'condiction' dict.fstdx
```

Fuzzy search based on edit distance 

```
fstdtools search -g 'testingsx'  test.fstdx
```

Prefix distance with prior suffix search from multiple fstdx files

```
fstdtools search -P 2 -k 振り返ってるのは  -x "する" -x "う" -x "く" -x "ぐ" -x "す" -x "つ" -x "ぬ" -x "ぶ" -x "む" -x "る" -x "い" -x "하다" -x "다" -f dict.fstdx　
```

## Reference

* https://github.com/MouJieQin/fstd
* https://github.com/liuyug/mdict-utils
* https://bitbucket.org/xwang/mdict-analysis
* https://github.com/zhansliu/writemdict
