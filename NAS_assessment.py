import csv, json, os, re
from typing import Iterable
import unittest
import fnmatch

#  Database
class Record(dict):
    categories = ["name", "address", "phone number"]

    def __str__(self):
        """ Overwrite dict string representation for a nicer output formatting """
        output = ""
        for key, value in self.items():
            key += ":"
            output += f"{key:<15} {value}\n"
        output = output.strip()
        return output


class Format():
    """ Abstract base class for Format creation """

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def getName(self):
        return self.name

    def write(self, record: "Record", fName: str) -> bool:
        raise NotImplementedError
        return False

    def getRecords(self, fName: str) -> list:
        raise NotImplementedError
        return []


class CSVFormat(Format):
    def __init__(self):
        super().__init__("csv")

    def write(self, record: Record, fName: str) -> bool:
        """
        Writes a record into the csv data file
        """
        success = False
        exists = os.path.isfile(fName)
        with open(fName, 'a', newline='') as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(Record.categories)
            writer.writerow(record.values())
            success = True

        return success

    def getRecords(self, fName: str) -> list:
        """
        Reads all of the entries in the csv data file and
        returns them as a list of records

        Returns an empty list if no data or data file present
        """
        records = []
        if os.path.isfile(fName):
            with open(fName, 'r') as f:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    record = Record()
                    for index, value in enumerate(row):
                        record[Record.categories[index]] = value
                    records.append(record)
        return records


class JSONFormat(Format):
    def __init__(self):
        super().__init__("json")

    def write(self, record: Record, fName: str) -> bool:
        """
        Writes a record into the json data file
        """
        success = False
        if not os.path.isfile(fName):
            with open(fName, "w") as f:
                json.dump({"records": []}, f, indent=4)
        with open(fName, "r+") as f:
            data = json.load(f)
            data["records"].append(record)
            f.seek(0)
            json.dump(data, f, indent=4)
            success = True
        return success

    def getRecords(self, fName: str) -> list:
        """
        Reads all of the entries in the json data file and
        returns them as a list of records

        Returns an empty list if no data or data file present
        """
        if os.path.isfile(fName):
            with open(fName, "r") as f:
                data = json.load(f)
                key = list(data.keys())[0]
                records = [Record(record) for record in data[key]]
                return records
        return []


class Database():
    def __init__(self, fileName, fileFormat):
        self.formats = self.__configFormats()
        self.currentFormat = fileFormat
        self.fileName = fileName
        if self.currentFormat not in self.formats.keys():
            print ('ERROR: file format {} is not supported'.format(self.currentFormat))
        self.dataFile = f"{fileName}.{self.currentFormat}"

    def add(self, newRecord: Record) -> bool:
        """
        adds a record to a database data file,
        using the 'type', a specified format

        Returns success status
        """
        return self.formats[self.currentFormat].write(newRecord, f"{self.dataFile}")

    def importRecords(self, fName: str) -> bool:
        """
        Imports records from a supported file type into the database

        Returns success status
        """
        success = False
        format = fName.strip().split('.')[1]
        if format in self.formats.keys():
            records = self.formats[format].getRecords(fName)
            for record in records:
                self.formats[self.currentFormat].write(record, self.dataFile)
            success = True
        return success

    def convert(self, newFormat: str) -> bool:
        """
        Converts the database from one format to another

        returns a boolean denoting success or failure to convert
        """
        if newFormat == self.currentFormat:
            return True
        if not os.path.isfile(self.dataFile):
            self.currentFormat = newFormat
            return True
        if newFormat in self.formats.keys():
            records = self.formats[self.currentFormat].getRecords(self.dataFile)
            newFile = f"{self.fileName}.{newFormat}"
            if os.path.isfile(newFile):
                os.remove(newFile)
            for record in records:
                self.add(record, newFormat)
            if self.formats[newFormat].getRecords(newFile) == records:
                os.remove(self.dataFile)
                self.currentFormat = newFormat
                self.dataFile = newFile
                return True
            else:
                os.remove(newFile)
                return False
        return False

    def getRecords(self) -> list:
        """ returns a list containing all stored records"""
        return self.formats[self.currentFormat].getRecords(self.dataFile)

    def getFormats(self) -> tuple:
        """ returns a tuple containing (dict of formats, current format) """
        return (self.formats, self.currentFormat)

    def __iter__(self):
        """ Determines how a database gets iterated over """
        for record in self.formats[self.currentFormat].getRecords(self.dataFile):
            yield record

    def __configFormats(self) -> dict:
        """	New storage formats get added here.	"""
        formats = {}
        formats['csv'] = CSVFormat()
        formats['json'] = JSONFormat()
        return formats

    def clean(self):
        """ Deletes the current data file"""
        if os.path.isfile(self.dataFile):
            os.remove(self.dataFile)

    def filter(self, valueSelected, searchItem):
        """ Filter the database using Glob syntax"""
        filterResults = []
        for entry in self.getRecords():
            if fnmatch.fnmatch(entry[valueSelected], searchItem):
                filterResults.append(entry)
            elif ',' in searchItem:
                for subItem in searchItem:
                    if entry[valueSelected] == subItem:
                        filterResults.append(entry)

        return filterResults

#  Command line interface
class Interface():
    def __init__(self):
        self.continuePrompt = True
        self.fileName = None
        self.fileType = None

    def createDatabase(self):
        self.database = Database(self.fileName, self.dataType)

    def startingPrompt(self):
        """ Specify target file and file type for the interface"""
        print("Welcome! Please specify the file name:")
        self.fileName = input("> ")

        print("Please specify the file type (currently supported formats: csv and json):")
        self.fileType = input("> ")

        self.database = Database(self.fileName, self.fileType)
        print("Database Initialized.")

    def prompt(self):
        """ Main driver of the command line interface """
        print("Please enter a command, type 'help' for list of commands:")
        while (self.continuePrompt):
            value = input("> ")
            self.__processCommand(value)
        return

    def __processCommand(self, command: str):
        """
        Helper function to process the commands recieved from user input prompts
        """
        command = command.strip().lower()
        if len(command) == 0:
            return

        if command == "help":
            self.__listCommands()

        elif command == "add":
            dataDict = {}
            for value in Record.categories:
                dataDict[value] = input(f"Please enter {value}: ").strip()
            newRecord = Record(dataDict)
            if self.database.add(newRecord):
                print("\nThe following record:")
                self.__prettyPrint([newRecord])
                print("has been added to the database!")
            else:
                print("ERROR: Failed to add new record to the database")

        elif command == "import":
            fName = input("File name?\n>> ").strip()
            if self.database.importRecords(fName):
                print(f"Records from {fName} have been added to the database")
            else:
                print(f"Unable to import records from {fName}")

        elif command == "filter":
            options = ""
            for value in Record.categories:
                options += f"{value}, "
            options = options[:-2]
            valueSelected = input(
                f"What are you searching for? Options: {options}\n>> ").strip().lower()
            if valueSelected in Record.categories:
                searchItem = input(f"Enter {valueSelected} to be found\n>>> ").strip()
                records = self.database.filter(valueSelected, searchItem)
                print("Results:")
                self.__prettyPrint(records)
            else:
                print(f"{valueSelected}s are not recorded at this time")

        elif command == "formats":
            self.__listFormats()

        elif command == "display":
            format = input(f"Format? Options: text, html\n>> ").strip().lower()
            if format == "text":
                self.__prettyPrint(self.database)
            elif format == "html":
                # Create an html file
                with open(f"html_display.html", 'w') as f:
                    for record in self.database:
                        f.write("<ul>")
                        for key, value in record.items():
                            f.write(f"<li>{key}: {value}</li>")
                        f.write("</ul><hr>")
                print("html file created!")
            else:
                print(f"{format} is not available at this time")

        elif command == "convert":
            print("Choose new format")
            self.__listFormats()
            newFormat = input(f">> ").strip().lower()
            if newFormat in self.database.getFormats()[0].keys():
                if self.database.convert(newFormat):
                    print(f"Database has been converted to {newFormat}!")
                else:
                    print(f"ERROR: Failed to converted database to {newFormat}")
            else:
                print(f"{newFormat} is not available at this time")

        elif command == "quit":
            self.continuePrompt = False
            print("Have a nice day!")
            return

        else:
            print(f"'{command}' is an invalid command, type 'help' for valid commands.")
        return

    def __prettyPrint(self, records: Iterable):
        """" Helper function that prints records out in a nice to read format """
        starCount = 30
        print("*" * starCount)
        for record in records:
            print(record)
            print("*" * starCount)
        return

    def __listFormats(self):
        """ Helper function for when all available formats need to be printed for the user to see
        """
        formatTypes, currentFormat = self.database.getFormats()
        print(f"Current: {currentFormat}")
        print("Available:", end=" ")
        for format in formatTypes:
            print(format, end=" ")
        print()

    def __listCommands(self):
        """
        Helper function that prints information about the commands.
        When adding a command, make sure to update the valid commands list.
        """
        print("  Valid Commmands:")
        validCommands = [
            ("help", "lists all valid commands"),
            ("add", "add a new entry to the database"),
            ("import",
             "imports records from a supported file type, and writes them to the data file"),
            ("filter", "search for items within the database"),
            ("formats", "list current storage format as well as all supported storage formats"),
            ("display", "displays the database in a human readable format"),
            ("convert", "converts database from one format to another"),
            ("quit", "exit the command line interface")
        ]
        for command, info in validCommands:
            print(f"  {command:<12}{info}")
        return


#  Unit tests
class T0_test_add_and_getRecords(unittest.TestCase):

    def test_add_record_csv(self):
        print("\nTesting add and getRecords with one record.  csv file")
        database = Database("test0Data", 'csv')
        database.clean()
        record = Record(
            {"name": "John Doe", "address": "123 Street street", "phone number": "555-5555"})
        database.add(record)
        recordCheck = database.getRecords()[0]
        self.assertEqual(record, recordCheck)
        database.clean()
        print("OK\n")

    def test_add_record_json(self):
        print("\nTesting add and getRecords with one record. json file")
        database = Database("test0Data", 'json')
        database.clean()
        record = Record(
            {"name": "John Doe", "address": "123 Street street", "phone number": "555-5555"})
        database.add(record)
        recordCheck = database.getRecords()[0]
        self.assertEqual(record, recordCheck)
        database.clean()
        print("OK\n")

    def test_filter_user(self):
        print("\nTesting filter user")
        database = Database("testFilter", 'csv')
        database.clean()
        record = Record(
            {"name": "John Doe", "address": "123 Street street", "phone number": "555-5555"})
        database.add(record)
        record = Record(
            {"name": "George Carlin", "address": "123 Street street", "phone number": "555-5555"})
        database.add(record)
        result = (database.filter('name', 'George*'))
        database.clean()

        if result == [{
            'name': 'George Carlin',
            'address': '123 Street street',
            'phone number': '555-5555'}]:
            print ("OK\n")
        else:
            raise AssertionError


#  Program driver
def main():
    """ Creates and launches the command line interface """
    interface = Interface()
    interface.startingPrompt()
    interface.prompt()
    return


if __name__ == "__main__":
    main()