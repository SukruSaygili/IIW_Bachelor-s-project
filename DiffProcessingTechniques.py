'''
************************************************************
- Author: Sükrü Saygili
- Date: 27/04/2025
- Title: Iterated Von Neumann Processing and Other Techniques
- Description: This script implements Von Neumann processing, XOR processing, and residual processing on binary data.
               Together, these techniques are used to implement the iterated Von Neumann processing.
- Code version: 1.0
- Type: source code
*************************************************************
'''


def vonNeumannProcessing(data):
    """Apply Von Neumann processing on the input binary data."""
    result = []
    for i in range(0, len(data) - 1, 2):  # process bit pairs
        pair = data[i:i+2]
        if pair == '10':
            result.append('0')
        elif pair == '01':
            result.append('1')
    return ''.join(result)

def xorProcessing(data):
    """Generate the SXOR sequence."""
    result = []
    for i in range(0, len(data) - 1, 2):  # process bit pairs
        pair = data[i:i+2]
        if pair == '01' or pair == '10':
            result.append('1')
        else:
            result.append('0')
    return ''.join(result)

def residualProcessing(data):
    """Generate the SR sequence."""
    result = []
    for i in range(0, len(data) - 1, 2):  # process bit pairs
        pair = data[i:i+2]
        if pair == '11':
            result.append('1')
        elif pair == '00':
            result.append('0')
    return ''.join(result)

def iteratedVonNeumann(data):
    """Generate SVN, SXOR, and SR sequences and cascade them in the order of occurrence."""
    cascaded_result = []
    
    # Process each bit pair and cascade results
    for i in range(0, len(data) - 1, 2):  # process bit pairs
        pair = data[i:i+2]
        
        # Initialize placeholders for SVN, SXOR, SR
        svn_bit = None
        sxor_bit = None
        sr_bit = None
        
        # Determine the values based on the pair
        if pair == '00':
            sxor_bit = '0'
            sr_bit = '0'
        elif pair == '01':
            svn_bit = '1'
            sxor_bit = '1'
        elif pair == '10':
            svn_bit = '0'
            sxor_bit = '1'
        elif pair == '11':
            sxor_bit = '0'
            sr_bit = '1'
        
        # Cascade the bits in the order: svn, sxor, sr
        if svn_bit is not None:
            cascaded_result.append(svn_bit)
        if sxor_bit is not None:
            cascaded_result.append(sxor_bit)
        if sr_bit is not None:
            cascaded_result.append(sr_bit)

    return ''.join(cascaded_result)

def processFile(inputFileName):
    # Read the input file
    with open(inputFileName, 'r') as file:
        data = file.read().strip()

    # Generate the sequences
    vn_result = vonNeumannProcessing(data)
    sxor_result = xorProcessing(data)
    sr_result = residualProcessing(data)

    # Generate the cascaded output
    cascaded_result = iteratedVonNeumann(data)

    # Write the results to different files
    with open('von_neumann_output.txt', 'w') as file:
        file.write(vn_result)

    with open('sxor_output.txt', 'w') as file:
        file.write(sxor_result)

    with open('sr_output.txt', 'w') as file:
        file.write(sr_result)
    
    with open('iterated_von_neumann.txt', 'w') as file:
        file.write(cascaded_result)

    print("Processing complete. Three output files generated:")
    print("- von_neumann_output.txt")
    print("- sxor_output.txt")
    print("- sr_output.txt")
    print("- iterated_von_neumann.txt")

inputFileName = 'input.txt'
processFile(inputFileName)