# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import io

from django import forms
from django.utils.translation import ugettext_lazy as _
from cosinnus.models.user_import import CosinnusUserImportProcessor


class CosinusUserImportCSVForm(forms.Form):

    csv = forms.FileField()

    def clean_csv(self):
        csv_file = self.cleaned_data['csv']
        reader = self.process_csv(csv_file)
        _header = next(reader, None)
        processed_header = self.process_and_validate_header(_header)
        rows = self.process_and_validate_data(reader)
        
        # check if all required columns are in the CSV
        missing_headers = []
        for required_column_name in CosinnusUserImportProcessor.REQUIRED_CSV_IMPORT_COLUMN_HEADERS:
            if required_column_name.lower().strip() not in processed_header:
                missing_headers.append(required_column_name)
        if missing_headers:    
            raise forms.ValidationError(_(f'Some required columns are not present in the CSV: {missing_headers}!'))
        
        # check if all rows and processed_header are the same length
        mismatched_rows = []
        for i, row in enumerate(rows):
            if len(row) != len(processed_header):
                mismatched_rows.append(i)
        if mismatched_rows:
            raise forms.ValidationError(_(f'Rows on these line numbers did not have the same number of items ({len(processed_header)}) as the header: {", ".join(mismatched_rows)}!'))
        
        # make a datadict, combining the headers with each row, ignoring any columns not found in KNOWN_CSV_IMPORT_COLUMNS_HEADERS
        data_dict_list, ignored_columns = self.make_data_dict_list(processed_header, rows)
        
        return {
            'header': processed_header,
            'rows': rows,
            'data_dict_list': data_dict_list,
            'ignored_columns': ignored_columns,
        }
        
    def process_and_validate_header(self, header):
        """ Cleans and validates header for no unnamed columns """
        cleaned_header = self.clean_row_data(header)
        processed_header = []
        for item in cleaned_header:
            item = item.strip().lower()
            if item:
                processed_header.append(item)
            else:
                raise forms.ValidationError(_(f'Some CSV headers did not have a name!'))
        return processed_header

    def process_and_validate_data(self, reader):
        data = []
        for row in reader:
            cleaned_row = self.clean_row_data(row)
            if row:
                data.append(cleaned_row)
        return data

    def process_csv(self, csv_file):
        try:
            file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(file)
            dialect = csv.Sniffer().sniff(io_string.read(102400000), delimiters=";,")
            io_string.seek(0)
            reader = csv.reader(io_string, dialect)
            return reader
        except UnicodeDecodeError:
            raise forms.ValidationError(_("This is not a valid CSV File"))
        except csv.Error as e:
            raise forms.ValidationError(_("CSV could not be parsed. Please use ',' or ';' as delimiter."))
    
    def make_data_dict_list(self, header, rows):
        """ Makes a datadict, combining the headers with each row, ignoring any columns not found in KNOWN_CSV_IMPORT_COLUMNS_HEADERS """ 
        lowercase_known_columns = [col.strip().lower() for col in CosinnusUserImportProcessor.KNOWN_CSV_IMPORT_COLUMNS_HEADERS]
        data_dict_list = []
        ignored_columns = []
        for row_counter, row in enumerate(rows):
            # add a row counter
            data_item = {'ROW_NUM': row_counter+1}
            for i, column_name in enumerate(header):
                # skip unknown columns
                column_name = column_name.strip()
                if column_name.lower() not in lowercase_known_columns:
                    if not column_name in ignored_columns:
                        ignored_columns.append(column_name)
                    continue
                data_item[column_name] = row[i]
            data_dict_list.append(data_item)
        return data_dict_list, ignored_columns
    
    def clean_row_data(self, row):
        """ Strips whitespaces off of each row item """
        cleaned_row = []
        for entry in row:
            cleaned_row.append(entry.strip())
        return cleaned_row
