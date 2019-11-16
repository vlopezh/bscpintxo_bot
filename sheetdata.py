from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from itertools import islice
from unidecode import unidecode
import locale
import tabulate
import sys

class SheetDataException(Exception):
    pass

class SheetData:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    DATA_RANGE = 'Votaciones!A1:Z30'
    VOTE_THRESHOLD = 0.05
    CHOICES_LEN = 12

    def __init__(self, spreadsheet_id):
        # Spreadsheet raw values
        self._values = None
        # Spreadsheet data parsed into a dictionary
        self._data = None
        # Choices ...
        self._choices = None

        # Load raw data and parse it
        self._load_google_sheet(spreadsheet_id)
        self._parse_data()


    def _load_google_sheet(self, spreadsheet_id):
        """ Load Google Spreadsheet into self._values """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'google_credentials.json', SheetData.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        # Get locale
        props = sheet.get(spreadsheetId=spreadsheet_id).execute()
        self._locale = props['properties']['locale']

        # Get values
        result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                    range=SheetData.DATA_RANGE).execute()
        self._values = result.get('values', [])

        if not self._values:
            # FIXME: use logging
            print("Cannot load Sheet data")
            sys.exit(1)


    def _parse_data(self):
        """ Parse data from self._values into self._data

        self._data will be a dictionary of the form:
            {
                'people' : [ {'name': <string>, 'votes': [<float>*] }* ],
                'places' : [ {'name': <string>, 'time': <float> }* ]
            }
        """
        self._data = {'people': [], 'places': []}

        # Create 'people' from cells [A5, A6, ...] and populate their votes at [C5:Z5, C6:Z6, ...]
        for n, cell in enumerate(islice(self._values[0], 4, None)):
            person = {'name': cell, 'votes': []}

            # Obtain votes
            votes = []
            for row in islice(self._values, 2, None):
                vote = self._cell_to_float(row, 4+n)
                votes.append(vote)

            # Normalize votes
            sum_of_abs = sum([abs(v) for v in votes])
            for v in votes:
                person['votes'].append(v/sum_of_abs)

            self._data['people'].append(person)

        # Create 'places' from cells [C3:Z3] with time [C4:Z4]
        for row in islice(self._values, 2, None):
            place = {}
            place['name'] = row[2]
            place['time'] = self._cell_to_float(row, 3)
            self._data['places'].append(place)


    def _cell_to_float(self, row, i):
        locale.setlocale(locale.LC_NUMERIC, self._locale)
        try:
            return locale.atof(row[i])
        except (IndexError, ValueError) as e:
            return 0.0


    def compute_choices(self, participants=None):
        """ Compute choices and their probability given a participants list

        participants -- list of participant names to include in the choices

        self._choices will be a dictionary of the form:
            {
                'participants' : [ <string>* ],
                'chances' : [ {'place': <string>, 'weight': <float>, 'perc': <float>}* ]
            }

        """
        self._choices = {'participants': [], 'chances': []}

        # If 'participants' is provided, validate the ones present in the parsed data
        if participants:
            # construct a new list of participants unidecoded and lower-case to compare
            participants = [unidecode(participant).lower() for participant in participants]
            for person in self._data['people']:
                if unidecode(person['name']).lower() in participants:
                    self._choices['participants'].append(person['name'])
        # Otherwise use all the people as participants.
        else:
            self._choices['participants'] = [person['name'] for person in self._data['people']]

        # Iterate all places to construct the chances based on the participants
        total_weight = 0
        for num, place in enumerate(self.places):
            votes = [ person['votes'][num]
                        for person in self._data['people']
                        if person['name'] in self._choices['participants']
                    ]
            try:
                weight = int((sum(votes) / len(votes)) / SheetData.VOTE_THRESHOLD)
            except ZeroDivisionError:
                raise SheetDataException
            weight = weight if weight > 0 else 0
            total_weight += weight
            self._choices['chances'].append({'place': place, 'weight': weight})

        # Iterate the dictionary again to compute percentages
        for chance in self._choices['chances']:
            chance['perc'] = float(chance['weight']) / total_weight * 100

        self._choices['chances'].sort(key=lambda x: x['weight'], reverse=True)


    def get_choices_table(self, hide_zeroes=False):
        max_len = SheetData.CHOICES_LEN
        table = []
        for chance in self.choices['chances']:
            # Stop iterating if weight is 0 (the list is sorted, we are done)
            if chance['weight'] == 0 and hide_zeroes:
                break

            # Shorten place name
            name = chance['place']
            name = name if len(name) < max_len else name[:max_len-4] + '...'

            table.append([name, chance['weight'], chance['perc']])

        return tabulate.tabulate(table, self.headers, floatfmt='.2f')


    @property
    def headers(self):
        return ['Sitio', 'Peso', '%']

    @property
    def people(self):
        return [person['name'] for person in self._data['people']]

    @property
    def places(self):
        return [place['name'] for place in self._data['places']]

    @property
    def choices(self):
        if not self._choices:
            self.compute_choices()
        return self._choices

    @property
    def choices_places(self):
        return [chance['place'] for chance in self.choices['chances']]

    @property
    def choices_weights(self):
        return [chance['weight'] for chance in self.choices['chances']]

    @property
    def choices_percentages(self):
        return [chance['perc'] for chance in self.choices['chances']]

    @property
    def choices_participants(self):
        return self.choices['participants']

    @property
    def choices_summary(self):
        output = []
        for chance in self.choices['chances']:
            if chance['weight'] > 0:
                output.append('{0} {1:.2f}%'.format(chance['place'], chance['perc']))
        return ', '.join(output)

