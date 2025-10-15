# ruff: noqa :E501
from appconf import AppConf
from django.conf import settings  # noqa


class CosinnusDeckDefaultSettings(AppConf):
    """Settings without a prefix namespace to provide default setting values for other apps.
    These are settings used by default in cosinnus apps, such as avatar dimensions, etc.
    """

    class Meta(object):
        prefix = ''

    # Enable migration of user decks to group boards. Only needed if users could create decks directly in the nc app.
    COSINNUS_DECK_MIGRATE_USER_DECKS = False

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
                            '<details class="details">'
                            '    <summary>🇬🇧 Show English version...</summary>'
                            '    <div data-type="detailsContent"><h3>Welcome to your task board!</h3>'
                            '        <p>Here you can organise the collaboration within your group/project – simple, flexible and clear.</p>'
                            '        <p></p>'
                            '        <p>💡 The following <strong>tips and tricks</strong> are designed to help you use your board:</p>'
                            '        <ul>'
                            '            <li><p>The tasks on this board are organised into <strong>lists</strong> (= columns).</p>'
                            '                <ul>'
                            '                    <li><p>You can move tasks between lists using <u>drag & drop</u>.</p></li>'
                            '                    <li><p>The lists should correspond to the <u>processing status</u> of the tasks.</p></li>'
                            '                    <li><p>The division <em>To Do</em> → <em>Doing</em> →'
                            '                        <em>Done</em> is only a suggestion. You can create your own lists that correspond to your workflow.'
                            '                    </p></li>'
                            '                </ul>'
                            '            </li>'
                            '            <li><p>Give your tasks appropriate'
                            "                <strong>labels</strong>. The labels can indicate the topic (e.g. 'public relations') or the priority of the task."
                            '            </p></li>'
                            '        </ul>'
                            '        <blockquote>'
                            '            <p>⚠️ Permissions: Only group/project admins can create, edit or delete lists and labels. However, individual tasks can be created, edited or deleted by all members (even tasks that were created by others). Non-members do not have access to your board and the tasks it contains.</p>'
                            '        </blockquote>'
                            '        <ul>'
                            '            <li><p>Specify a'
                            '                <strong>due date</strong> for each of your tasks so that you can keep track of your deadlines.</p></li>'
                            '            <li><p>By'
                            '                <strong>assigning tasks to the responsible members</strong>, you can keep track of who is taking care of what.'
                            '            </p></li>'
                            "            <li><p>Using the board's"
                            '                <strong>filter function</strong> (bottom left), you can filter tasks by label, assignee, due date and status (open vs closed). This allows you to keep track of even very full boards that are used by many members for different topics.'
                            '            </p></li>'
                            '            <li><p>The text fields for the task description and comments offer you a'
                            '                <strong>wide range of text formatting options</strong> that you can insert using the toolbar at the bottom, including:'
                            '            </p>'
                            '                <ul>'
                            '                    <li><p>Checkbox lists for subtasks</p></li>'
                            '                    <li><p>Expandable areas</p></li>'
                            '                    <li><p>Inserting graphics from the clipboard using <u>copy & paste</u></p></li>'
                            '                    <li><p>Uploading attachments via <u>drag & drop</u></p></li>'
                            '                </ul>'
                            '            </li>'
                            '            <li><p>You can reply to comments to create a'
                            '                <strong>comment thread</strong>. That way, you can keep each discussion separate and organized.</p>'
                            '                <ul>'
                            '                    <li><p>You can mark a thread as'
                            '                        <em>resolved</em>. The replies of a resolved thread are collapsed for everyone by default. If necessarry, the replies can be expanded manually or the thread can be marked as'
                            '                        <em>unresolved</em>.</p></li>'
                            '                </ul>'
                            '            </li>'
                            '        </ul>'
                            '        <p></p>'
                            '        <p>With this knowledge, you are well equipped to get the most out of your task board and collaborate effectively!</p>'
                            "        <blockquote><p>ℹ️ If you no longer need this 'HOW TO...' task, you can simply delete it.</p></blockquote>"
                            '    </div>'
                            '</details>'
                            '<details class="details" open="">'
                            '    <summary>🇩🇪 Deutsche Version anzeigen...</summary>'
                            '    <div data-type="detailsContent"><h3>Willkommen auf eurem Aufgaben-Board!</h3>'
                            '        <p>Hier könnt ihr die Zusammenarbeit in eurer Gruppe/eurem Projekt organisieren - einfach, flexibel und übersichtlich.</p>'
                            '        <p></p>'
                            '        <p>💡 Die folgenden <strong>Tipps und Tricks</strong> sollen euch bei der Nutzung eures Boards helfen:</p>'
                            '        <ul>'
                            '            <li><p>Die Aufgaben auf diesem Board werden in <strong>Listen</strong> (= Spalten) geordnet.</p>'
                            '                <ul>'
                            '                    <li><p>Ihr könnt die Aufgaben per <u>Drag & Drop</u> zwischen den Listen verschieben.</p></li>'
                            '                    <li><p>Die Listen sollten dem <u>Bearbeitungsstatus</u> der Aufgaben entsprechen.</p></li>'
                            '                    <li><p>Die Aufteilung <em>To Do</em> → <em>Doing</em> →'
                            '                        <em>Done</em> ist nur ein Vorschlag. Ihr könnt eure eigenen Listen erstellen, die eurem Workflow entsprechen.'
                            '                    </p></li>'
                            '                </ul>'
                            '            </li>'
                            '            <li><p>Gebt euren Aufgaben passende'
                            '                <strong>Labels</strong>. Die Labels können den Themenbereich (z. B. "Öffentlichkeitsarbeit") oder die Priorität der Aufgabe angeben.'
                            '            </p></li>'
                            '        </ul>'
                            '        <blockquote>'
                            '            <p>⚠️ Berechtigungen: Nur Gruppen-/Projekt-Admins können Listen und Labels erstellen, bearbeiten oder löschen. Einzelne Aufgaben können jedoch von allen Mitgliedern erstellt, bearbeitet oder gelöscht werden (auch Aufgaben, die andere erstellt haben). Nicht-Mitglieder haben keinen Zugriff auf euer Board und die Aufgaben darin.</p>'
                            '        </blockquote>'
                            '        <ul>'
                            '            <li><p>Gebt bei euren Aufgaben jeweils ein'
                            '                <strong>Fälligkeitsdatum</strong> an, damit ihr eure Deadlines im Blick habt.</p></li>'
                            '            <li><p>Indem ihr eure Aufgaben den'
                            '                <strong>zuständigen Mitgliedern zuweist</strong>, behaltet ihr den Überlick darüber, wer sich worum kümmert.'
                            '            </p></li>'
                            '            <li><p>Über die'
                            '                <strong>Filter-Funktion</strong> des Boards (links unten) könnt ihr die Aufgaben nach Labels, Zugewiesenen, Fälligkeitsdatum oder Status (offen vs. erledigt) filtern. Dadurch könnt ihr auch auf sehr vollen Boards, die von vielen Mitgliedern für verschiedene Themenbereiche genutzt werden, immer den Überblick behalten.'
                            '            </p></li>'
                            '            <li><p>Die Textfelder der Aufgaben-Beschreibung und der Kommentare bieten euch'
                            '                <strong>vielfältige Möglichkeiten der Text-Formatierung</strong>, die ihr über die Werkzeug-Leiste einfügen könnt, darunter:'
                            '            </p>'
                            '                <ul>'
                            '                    <li><p>Checkbox-Listen für Unter-Aufgaben</p></li>'
                            '                    <li><p>Ausklappbare Bereiche</p></li>'
                            '                    <li><p>Einfügen von Grafiken aus der Zwischenablage per <u>Copy & Paste</u></p></li>'
                            '                    <li><p>Hochladen von Anhängen via <u>Drag & Drop</u></p></li>'
                            '                </ul>'
                            '            </li>'
                            '            <li><p>Ihr könnt auf Kommentare antworten, um einen'
                            '                <strong>Kommentar-Thread</strong> zu erstellen. Damit könnt ihr einzelne Diskussionen besser trennen und strukturieren.'
                            '            </p>'
                            '                <ul>'
                            '                    <li><p>Ihr könnt einen Thread als'
                            '                        <em>gelöst</em> markieren. Die Antworten in einem gelösten Thread sind für alle Mitglieder standardmäßig eingeklappt. Bei Bedarf können die Antworten manuell ausgeklappt oder der Thread wieder als'
                            '                        <em>ungelöst</em> markiert werden.</p></li>'
                            '                </ul>'
                            '            </li>'
                            '        </ul>'
                            '        <p></p>'
                            '        <p>Mit diesem Wissen seid ihr gut gewappnet, um das meiste aus eurem Aufgaben-Board herauszuholen und effektiv zusammenzuarbeiten!</p>'
                            '        <blockquote><p>ℹ️ Solltet ihr diese Aufgabe "HOW TO..." nicht mehr brauchen, könnt ihr sie einfach löschen.</p>'
                            '        </blockquote>'
                            '    </div>'
                            '</details>'
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
