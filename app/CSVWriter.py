from django.http.response import HttpResponse


class CSVWriter:
    """
    Class to convert Dataframe to CSV
    """
    def __init__(self, df, path=None):
        self.df = df
        self.path = path

    def convert_to_csv(self, filename=None):
        if self.path:
            # return the CSV path
            return self.path
        else:
            # return the CSV as a django response
            if not filename:
                raise Exception("Param 'filename' is required")
            if not filename.endswith("csv"):
                filename += ".csv"

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
            self.df.to_csv(path_or_buf=response, index=False)
            return response

    def close(self):
        del self.df
        del self.path
