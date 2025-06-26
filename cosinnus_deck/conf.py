# ruff: noqa :E501
from appconf import AppConf
from django.conf import settings  # noqa


class CosinnusDeckDefaultSettings(AppConf):
    """Settings without a prefix namespace to provide default setting values for other apps.
    These are settings used by default in cosinnus apps, such as avatar dimensions, etc.
    """

    class Meta(object):
        prefix = ''

    # Default labels created by the Deck app that are be automatically deleted when initializing a group board.
    COSINNUS_DECK_GROUP_BOARD_DELETE_DEFAULT_LABELS = ['Action needed', 'Finished', 'Later', 'To review']

    # Initial labels, stacks and cards that are automatically created for a new group board.
    # Available variables in card description: %(portal_url)s
    COSINNUS_DECK_GROUP_BOARD_INITIAL_CONTENT = {
        'labels': [('Prio1', 'e01b24'), ('Prio2', 'f6d32d'), ('Prio3', '7fb800')],
        'stacks': [
            {
                'title': 'To Do',
                'cards': [
                    {
                        'title': 'HOW TO...',
                        'description': (
                            '<details><summary>Show English version...</summary>\n\n'
                            '## Welcome to your task board!\n\n'
                            'Here you can organise collaboration within your group/project – simple, flexible and clear.\n\n'
                            '💡 The following **tips and tricks** are designed to help you use your board:\n'
                            '* The tasks on this board are organised into **lists** (= columns).\n'
                            '   * You can move tasks between lists using <u>drag & drop</u>.\n'
                            '   * The lists should correspond to the <u>processing status</u> of the tasks.\n'
                            '   * The division *To Do* → *Doing* → *Done* is only a suggestion. You can create <u>your own lists</u> that correspond to your workflow.\n'
                            '* Give your tasks appropriate **labels**. The labels can indicate the <u>topic</u> (e.g. ‘public relations’) or the <u>priority</u> of the task.\n\n'
                            '> ⚠️ **Permissions**: Only group/project admins can create, edit or delete lists and labels. However, individual tasks can be created, edited or deleted by all members (even tasks that were created by others). Non-members do not have access to your board and the tasks it contains.\n\n'
                            '* Specify a **due date** for each of your tasks so that you can keep track of your deadlines.\n'
                            '* By **assigning tasks to the responsible members**, you can keep track of who is taking care of what. The assigned members will also see their tasks in their [personal task board](%(portal_url)s/personal-board) ↗.\n'
                            "* Using the board's ** filter function ** (bottom left), you can filter tasks by label, assignee and due date. This allows you to keep track of even very full boards that are used by many members for different topics.\n"
                            '* The text fields for the task description and comments offer you a **wide range of text formatting options** that you can insert using the toolbar, including:\n'
                            '   * <u>Checkbox lists</u> for subtasks\n'
                            '   * <u>Tables</u>\n'
                            '   * <u>Expandable areas</u>\n'
                            '   * Inserting graphics from the clipboard using <u>copy & paste</u>\n'
                            '   * Uploading attachments and inserting graphics using <u>drag & drop</u>\n'
                            '* You can reply to comments to create a **comment thread**. The replies to the original comment can be expanded and collapsed.\n\n'
                            'With this knowledge, you are well equipped to get the most out of your task board and collaborate effectively! \n\n'
                            '> ℹ️ If you no longer need this ‘HOW TO...’ task, you can simply delete it.\n\n'
                            '</details>\n\n'
                            '<details open><summary>Deutsche Version anzeigen...</summary>\n\n'
                            '## Willkommen auf eurem Aufgaben-Board!\n\n'
                            'Hier könnt ihr die Zusammenarbeit in eurer Gruppe/eurem Projekt organisieren - einfach, flexibel und übersichtlich.\n\n'
                            '💡 Die folgenden **Tipps und Tricks** sollen euch bei der Nutzung eures Boards helfen:\n'
                            '* Die Aufgaben auf diesem Board werden in **Listen** (= Spalten) geordnet.\n'
                            '   * Ihr könnt die Aufgaben per <u>Drag & Drop</u> zwischen den Listen verschieben.\n'
                            '   * Die Listen sollten dem <u>Bearbeitungsstatus</u> der Aufgaben entsprechen.\n'
                            '   * Die Aufteilung *To Do* → *Doing* → *Done* ist nur ein Vorschlag. Ihr könnt <u>eure eigenen Listen</u> erstellen, die eurem Workflow entsprechen.\n'
                            '* Gebt euren Aufgaben passende **Labels**. Die Labels können den <u>Themenbereich</u> (z. B. "Öffentlichkeitsarbeit") oder die <u>Priorität</u> der Aufgabe angeben.\n\n'
                            '> ⚠️ **Berechtigungen**: Nur Gruppen-/Projekt-Admins können Listen und Labels erstellen, bearbeiten oder löschen. Einzelne Aufgaben können jedoch von allen Mitgliedern erstellt, bearbeitet oder gelöscht werden (auch Aufgaben, die andere erstellt haben). Nicht-Mitglieder haben keinen Zugriff auf euer Board und die Aufgaben darin.\n'
                            '* Gebt bei euren Aufgaben jeweils ein **Fälligkeitsdatum** an, damit ihr eure Deadlines im Blick habt.\n'
                            '* Indem ihr eure Aufgaben den **zuständigen Mitgliedern zuweist**, behaltet ihr den Überlick darüber, wer sich worum kümmert. Die zugewiesenen Mitglieder bekommen ihre Aufgaben auch in ihrem [persönlichen Aufgaben-Board](%(portal_url)s/personal-board) ↗ angezeigt.\n'
                            '* Über die **Filter-Funktion** des Boards (links unten) könnt ihr die Aufgabe nach Labels, Zugewiesenen und Fälligkeitsdatum filtern. Dadurch könnt ihr auch auf sehr vollen Boards, die von vielen Mitgliedern für verschiedene Themenbereiche genutzt werden, immer den Überblick behalten.\n'
                            '* Die Textfelder der Aufgaben-Beschreibung und der Kommentare bieten euch **vielfältige Möglichkeiten der Text-Formatierung**, die ihr über die Werkzeug-Leiste einfügen könnt, darunter:\n'
                            '   * <u>Checkbox-Listen</u> für Unter-Aufgaben\n'
                            '   * <u>Tabellen</u>\n'
                            '   * <u>Ausklappbare Bereiche</u>\n'
                            '   * Einfügen von Grafiken aus der Zwischenablage per <u>Copy & Paste</u>\n'
                            '   * Hochladen von Anhängen und Einfügen von Grafiken per <u>Drag & Drop</u>\n'
                            '* Ihr könnt auf Kommentare antworten, um einen **Kommentar-Thread** zu erstellen. Die Antworten auf den Original-Kommentar können ein- und ausgeklappt werden.\n\n'
                            'Mit diesem Wissen seid ihr gut gewappnet, um das meiste aus eurem Aufgaben-Board herauszuholen und effektiv zusammenzuarbeiten! \n\n'
                            '> ℹ️ Solltet ihr diese Aufgabe "HOW TO..." nicht mehr brauchen, könnt ihr sie einfach löschen.\n\n'
                            '</details>\n'
                        ),
                    }
                ],
            },
            {
                'title': 'Doing',
                'cards': [],
            },
            {
                'title': 'Done',
                'cards': [],
            },
        ],
    }
