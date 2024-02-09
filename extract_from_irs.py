import xml.etree.ElementTree as ET
import sys
import os
import csv
import copy


FIELDNAMES = [
    "FoundationName",
    "FoundationEIN",
    "TaxYear",
    "InputSource",
    "RecipientName",
    "RecipientEIN",
    "RecipientIRSSection",
    "RecipientStreet",
    "RecipientCity",
    "RecipientState",
    "RecipientZip",
    "RecipientRelationshipTxt",
    "RecipientFoundationStatusTxt",
    "GrantAmount",
    "GrantPurpose",
        ]

XML_NS = {
        'ef': 'http://www.irs.gov/efile',
        'xsi': "http://www.w3.org/2001/XMLSchema-instance",
        }
def extract_common(root):
    record = {}
    header = root.find('ef:ReturnHeader', XML_NS)

    record["InputSource"] = header.find('ef:ReturnTypeCd', XML_NS).text
    record["TaxYear"] = header.find('ef:TaxYr', XML_NS).text

    filer = header.find('ef:Filer', XML_NS)
    record["FoundationName"] = filer.find('ef:BusinessName/ef:BusinessNameLine1Txt', XML_NS).text
    record["FoundationEIN"] = filer.find('ef:EIN', XML_NS).text
    
    return record

def extract_address_into(element, record):
    record["RecipientStreet"]  = "UNKNOWN"
    record["RecipientCity"]  = "UNKNOWN"
    record["RecipientState"]  = "UNKNOWN"
    record["RecipientZip"]  = "UNKNOWN"

    bit = element.find('ef:AddressLine1Txt', XML_NS)
    if bit is not None:
        record["RecipientStreet"]  = bit.text

    bit = element.find('ef:CityNm', XML_NS)
    if bit is not None:
        record["RecipientCity"]  = bit.text

    bit = element.find('ef:StateAbreviationCd', XML_NS)
    if bit is not None:
        record["RecipientState"]  = bit.text

    bit = element.find('ef:ZipCd', XML_NS)
    if bit is not None:
        record["RecipientZip"]  = bit.text

def extract_990(root, common):
    records = []
    for recipient in root.findall('ef:ReturnData/ef:IRS990ScheduleI/ef:RecipientTable', XML_NS):
        recip = copy.copy(common)
        recip["RecipientName"] = recipient.find('ef:RecipientBusinessName/ef:BusinessNameLine1Txt', XML_NS).text
        ein = recipient.find('ef:RecipientEIN', XML_NS)
        if ein is not None:
            recip["RecipientEIN"] = ein.text
        else:
            recip["RecipientEIN"] = "UNKNOWN"

        
        section = recipient.find('ef:IRCSectionDesc', XML_NS)
        if section is not None:
            recip["RecipientIRSSection"] = section.text
        else:
            recip["RecipientIRSSection"] = "UNKNOWN"

        extract_address_into(recipient.find("ef:USAddress", XML_NS), recip)
        recip["RecipientRelationshipTxt"]  = None
        recip["RecipientFoundationStatusTxt"]  = None

        cash =  recipient.find('ef:CashGrantAmt', XML_NS).text
        noncash =  recipient.find('ef:NonCashAssistanceAmt', XML_NS).text
        donation = "error"
        try:
            cash = int(cash)
            noncash = int(noncash)
            donation = str(cash + noncash)
        except ValueError:
            pass

        recip["GrantAmount"]  = donation
        recip["GrantPurpose"]  = recipient.find('ef:PurposeOfGrantTxt', XML_NS).text
        records.append(recip)
    return records

def extract_990PF(root, common):
    records = []
    for recipient in root.findall('ef:ReturnData/ef:IRS990PF/ef:SupplementaryInformationGrp/ef:GrantOrContributionPdDurYrGrp', XML_NS):
        recip = copy.copy(common)
        recip["RecipientName"] = recipient.find('ef:RecipientPersonNm', XML_NS).text

        ein = recipient.find('ef:RecipientEIN', XML_NS)
        if ein is not None:
            recip["RecipientEIN"] = ein.text

        recip["RecipientIRSSection"] = None
        extract_address_into(recipient.find('ef:RecipientUSAddress', XML_NS), recip)
        recip["RecipientRelationshipTxt"] = recipient.find('ef:RecipientRelationshipTxt', XML_NS).text
        recip["RecipientFoundationStatusTxt"] = recipient.find('ef:RecipientFoundationStatusTxt', XML_NS).text

        recip["GrantAmount"] = recipient.find('ef:Amt', XML_NS).text
        recip["GrantPurpose"] = recipient.find('ef:GrantOrContributionPurposeTxt', XML_NS).text
        records.append(recip)
    return records

def extract_donation_records(filepath):
    tree = parse(filepath)
    record = extract_common(tree)
    records = None
    if record["InputSource"] == "990":
        print("extracting %f as 990", filepath)
        records = extract_990(tree, record) 
    elif record["InputSource"] == "990PF":
        print("extracting %f as 990PF", filepath)
        records = extract_990PF(tree, record) 
    return records

def parse(path):
    tree = ET.parse(path)
    root = tree.getroot()
    return root


def find_files(dir_path):
    files = []
    for candidate in os.listdir(dir_path):
        if "_public." in candidate:
            files.append(os.path.join(dir_path, candidate))
    return files

def process_files_into(files, writer):
    for file in files:
        data = extract_donation_records(file)
        writer.writerows(data)

def main():
    print("searching", sys.argv[1])
    files = find_files(sys.argv[1])
    print(files)
    output_file = "recipients.csv"

    with open(output_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        writer.writeheader()
        process_files_into(files, writer)

if __name__ == "__main__":
    main()

