
class SimpleNotebook:
    def __init__(self, created=None, updated=None):
        self.created = created
        self.updated = updated
        self.notes = {}

    def __repr__(self):
        return "Notebook(created={} updated={} notes={})".format(self.created, self.updated, self.notes)


class SimpleNote:
    def __init__(self, created=None, updated=None):
        self.created = created
        self.updated = updated

    def __repr__(self):

        return "Note(created={} updated={})".format(self.created, self.updated)
