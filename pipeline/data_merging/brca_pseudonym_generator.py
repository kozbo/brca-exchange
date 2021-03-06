#!/usr/bin/env python

from __future__ import print_function, division
import argparse
import sys 
import os
import hgvs
import hgvs.parser as hgvs_parser
import hgvs.dataproviders.uta as hgvs_dataproviders_uta
import hgvs.variantmapper as hgvs_variantmapper
import hgvs.exceptions
import pyhgvs
import pyhgvs.utils as pyhgvs_utils
from pygr.seqdb import SequenceFileDB

'''
    Example run:
        ./brca_pseudonym_generator.py -j hg18.fa -k hg19.fa -l hg38.fa -r refseq_annotation.hg18.gp -s refseq_annotation.hg19.gp -t refseq_annotation.hg38.gp -i aggregated.tsv -o test.out -p > stdoutErrorLog.txt
    
    WARNING:
        Currently only works for insertion and deletion strings less than or equal to 100 bases long. Can be modified to be larger.
'''

def parse_args():
    """ 
    Description:
        function 'parse_args' parses arguments from command-line and returns an argparse
        object containing the arguments and their values. Default values are 'False' if option
        is not listed in the command, else the option value is set to True.
    """
    parser = argparse.ArgumentParser(description='Fill in hg18, hg19 genomic coordinates and cDNA hgvs strings in  merged BRCA variant dataset.')
    parser.add_argument('-i', '--inBRCA', type=argparse.FileType('r'),
        help='Input ENIGMA BRCA datatable file for conversion.')
    parser.add_argument('-j', '--inHg18', type=argparse.FileType('r'),
        help='Input hg18 reference genome fasta file.')
    parser.add_argument('-k', '--inHg19', type=argparse.FileType('r'),
        help='Input hg19 reference genome fasta file.')
    parser.add_argument('-l', '--inHg38', type=argparse.FileType('r'),
        help='Input hg38 reference genome fasta file.')
    parser.add_argument('-r', '--inRefSeq18', type=argparse.FileType('r'),
        help='Input refseq annotation hg18-based genepred file.')
    parser.add_argument('-s', '--inRefSeq19', type=argparse.FileType('r'),
        help='Input refseq annotation hg19-based genepred file.')
    parser.add_argument('-t', '--inRefSeq38', type=argparse.FileType('r'),
        help='Input refseq annotation hg38-based genepred file.')
    parser.add_argument('-p', '--calcProtein', dest='calcProtein', action='store_true', 
        help='Set flag for hgvs protein fill-in. May not result in complete fill-in.')
    parser.add_argument('-o', '--outBRCA', type=argparse.FileType('w'),
        help='Output filled in ENIGMA BRCA datatable file.')
    
    parser.set_defaults(calcProtein=False)
    options = parser.parse_args()
    return options

def main(args):

    options = parse_args()
    brcaFile = options.inBRCA
    hg18_fa = options.inHg18
    hg19_fa = options.inHg19
    hg38_fa = options.inHg38
    refSeq18 = options.inRefSeq18
    refSeq19 = options.inRefSeq19
    refSeq38 = options.inRefSeq38
    outputFile = options.outBRCA
    calcProtein = options.calcProtein
    
    hdp = hgvs_dataproviders_uta.connect()
    variantmapper = hgvs_variantmapper.EasyVariantMapper(hdp)
    hgvsparser = hgvs_parser.Parser()
    
    genome36 = SequenceFileDB(hg18_fa.name)
    genome37 = SequenceFileDB(hg19_fa.name)
    genome38 = SequenceFileDB(hg38_fa.name)
    
    transcripts36 = pyhgvs_utils.read_transcripts(refSeq18)
    transcripts37 = pyhgvs_utils.read_transcripts(refSeq19)
    transcripts38 = pyhgvs_utils.read_transcripts(refSeq38)
    
    def get_transcript36(name):
        return transcripts36.get(name)
    def get_transcript37(name):
        return transcripts37.get(name)
    def get_transcript38(name):
        return transcripts38.get(name)

    hgvsG36ColumnName = 'Genomic_Coordinate_hg36'
    hgvsG37ColumnName = 'Genomic_Coordinate_hg37'
    hgvsG38ColumnName = 'Genomic_Coordinate_hg38'
    refSeqColumnName = 'Reference_Sequence'
    hgvsCDNAColumnName = 'HGVS_cDNA'
    hgvsPColumnName = 'HGVS_Protein'

    labelLine = brcaFile.readline().rstrip().split('\t')
    writeLine = '\t'.join(labelLine)+'\n'
    outputFile.writelines(writeLine)

    # Store indexes of the relevant columns
    hgvsG36Index = labelLine.index(hgvsG36ColumnName)
    hgvsG37Index = labelLine.index(hgvsG37ColumnName)
    hgvsG38Index = labelLine.index(hgvsG38ColumnName)
    refSeqIndex = labelLine.index(refSeqColumnName)
    hgvsCDNAIndex = labelLine.index(hgvsCDNAColumnName)
    hgvsPIndex = labelLine.index(hgvsPColumnName)
    geneSymbolIndex = labelLine.index("Gene_Symbol")
    synonymIndex = labelLine.index("Synonyms") 
    
    refSeqBRCA1Transcripts = ['NM_007294.2', 'NM_007300.3', 'NM_007299.3', 'NM_007298.3', 'NM_007297.3', 'U14680.1']
    refSeqBRCA2Transcripts = ['U43746.1']
    
    for line in brcaFile:
        parsedLine = line.rstrip().split('\t')
        
        if parsedLine[geneSymbolIndex] == 'BRCA1': 
            parsedLine[refSeqIndex] = 'NM_007294.3'
        elif parsedLine[geneSymbolIndex] == 'BRCA2': 
            parsedLine[refSeqIndex] = 'NM_000059.3'
        
        # Format genomic variant position strings to contain relevant refseq strings 
        oldHgvsGenomic36 = parsedLine[refSeqIndex] + ':' + parsedLine[hgvsG36Index]
        oldHgvsGenomic37 = parsedLine[refSeqIndex] + ':' + parsedLine[hgvsG37Index]
        oldHgvsGenomic38 = parsedLine[refSeqIndex] + ':' + parsedLine[hgvsG38Index].split(',')[0]
        oldHgvsCDNA = parsedLine[refSeqIndex] + ':' + parsedLine[hgvsCDNAIndex]

        chrom38 = parsedLine[labelLine.index("Chr")]
        offset38 = parsedLine[labelLine.index("Pos")]
        ref38 = parsedLine[labelLine.index("Ref")]
        alt38 = parsedLine[labelLine.index("Alt")]
        print("working on variant", chrom38, offset38, ref38, alt38)
        
        # Edge cases to correct variant string formats for indels in order to be accepted by the counsyl parser
        if ref38 == '-': ref38 = ''
        if alt38 == '-': alt38 = ''
        if alt38 == 'None': alt38 = ''
        
        transcript38 = get_transcript38(parsedLine[refSeqIndex])
        transcript37 = get_transcript37(parsedLine[refSeqIndex])
        transcript36 = get_transcript36(parsedLine[refSeqIndex])
        
        # Normalize hgvs cdna string to fit what the counsyl hgvs parser determines to be the correct format
        cdna_coord = str(pyhgvs.format_hgvs_name("chr" + chrom38, int(offset38), ref38, alt38, genome38, transcript38, use_gene=False, max_allele_length=100))

        chrom38, offset38, ref38, alt38 = pyhgvs.parse_hgvs_name(cdna_coord, genome38, get_transcript=get_transcript38)
        chrom37, offset37, ref37, alt37 = pyhgvs.parse_hgvs_name(cdna_coord, genome37, get_transcript=get_transcript37)
        chrom36, offset36, ref36, alt36 = pyhgvs.parse_hgvs_name(cdna_coord, genome36, get_transcript=get_transcript36)
        
        # Generate transcript hgvs cdna synonym string
        if parsedLine[synonymIndex] == "-":
            synonymString = []
        elif parsedLine[synonymIndex] == "":
            synonymString = []
        else:
            synonymString = parsedLine[synonymIndex].split(",")

        if parsedLine[geneSymbolIndex] == 'BRCA1':
            for transcriptName in refSeqBRCA1Transcripts:
                transcript38 = get_transcript38(transcriptName)
                cdna_synonym = str(pyhgvs.format_hgvs_name(chrom38, int(offset38), ref38, alt38, genome38, transcript38, use_gene=False, max_allele_length=100))
                synonymString.append(cdna_synonym)
        elif parsedLine[geneSymbolIndex] == 'BRCA2':
            for transcriptName in refSeqBRCA2Transcripts:
                transcript38 = get_transcript38(transcriptName)
                cdna_synonym = str(pyhgvs.format_hgvs_name(chrom38, int(offset38), ref38, alt38, genome38, transcript38, use_gene=False, max_allele_length=100))
                synonymString.append(cdna_synonym)
        
        if calcProtein == True:
            #print('oldHgvsGenomic38:', oldHgvsGenomic38)
            #print('oldHgvsCDNA: ', oldHgvsCDNA)
            #print('cdna: ', cdna_coord)

            try:
                var_c1 = hgvsparser.parse_hgvs_variant(cdna_coord)
                protein_coord = variantmapper.c_to_p(var_c1)
            except hgvs.exceptions.HGVSParseError as e:
                print('hgvs.exceptions.HGVSParseError: ', e)
                print('GRCh38 Genomic change: ', '{0}:{1}:{2}>{3}'.format(chrom38,offset38,ref38,alt38))
                print('')
            #print('oldProtein: ', parsedLine[hgvsPIndex]) 
            #print('protein:', protein_coord)
            #print('')
        
        # write new data into line
        parsedLine[hgvsG36Index] = '{0}:{1}:{2}>{3}'.format(chrom36,offset36,ref36,alt36)
        parsedLine[hgvsG37Index] = '{0}:{1}:{2}>{3}'.format(chrom37,offset37,ref37,alt37)
        parsedLine[hgvsG38Index] = '{0}:{1}:{2}>{3}'.format(chrom38,offset38,ref38,alt38)
        parsedLine[labelLine.index("Hg37_Start")] = str(offset37)
        parsedLine[labelLine.index("Hg37_End")] = str(int(offset37) + len(ref38) - 1)
        parsedLine[labelLine.index("Hg36_Start")] = str(offset36)
        parsedLine[labelLine.index("Hg36_End")] = str(int(offset36) + len(ref38) - 1)


        parsedLine[hgvsCDNAIndex] = '{0}'.format(cdna_coord)
        if calcProtein == True: parsedLine[hgvsPIndex] = '{0}'.format(str(protein_coord))
        parsedLine[synonymIndex] = ','.join(synonymString)
        writeLine = '\t'.join(parsedLine)+'\n'
        outputFile.writelines(writeLine)
    
    hg18_fa.close()
    hg19_fa.close()
    hg38_fa.close()
    refSeq18.close()
    refSeq19.close()
    refSeq38.close()
    outputFile.close()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
