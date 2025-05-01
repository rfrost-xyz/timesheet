# ui.py
# Textual UI with Daily Overview, Filterable Selects, and Edit Mode

import datetime
import logging
from typing import Optional, Any, Dict, List, Tuple, NamedTuple

from textual.app import ComposeResult, RenderResult
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Header, Footer, Static, Label, Input, Select, DataTable, Placeholder, Button, OptionList
)
from textual.widget import Widget
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive, var
from textual import work, events
from textual.validation import Function, ValidationResult, Validator, Integer
from textual.coordinate import Coordinate
from textual.widgets.data_table import RowKey


# Import db functions and utils
import db
import utils
from config import TIME_INCREMENT_MINUTES

# --- Custom Messages ---
class ItemSelected(Message):
    """Message sent when an item is selected from FilterableSelect."""
    def __init__(self, control_id: str, item_id: Optional[int], item_name: Optional[str]) -> None:
        self.control_id = control_id
        self.item_id = item_id
        self.item_name = item_name
        super().__init__()

class LogSaved(Message):
    """Custom message when a log entry is saved (add or update)."""
    pass

# --- Custom Validator for Time Input ---
class DateTimeValidator(Validator):
    """Validates HH:MM format."""
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.success()
        try:
            datetime.datetime.strptime(value, "%H:%M")
            return self.success()
        except ValueError:
            return self.failure("Use HH:MM format.")


# --- Filterable Select Option Data Structure ---
class FilterableSelectOption(NamedTuple):
    """Data structure for options in FilterableSelect."""
    display: str
    id: Optional[int]

# --- Filterable Select Widget ---
class FilterableSelect(Container):
    """A widget combining an Input and OptionList for filterable selection."""

    DEFAULT_CSS = """
    FilterableSelect { height: auto; border: none; padding: 0; margin-bottom: 1; }
    FilterableSelect Input { border: round $accent; margin-bottom: 0; padding: 0 1; }
    FilterableSelect Input:focus { border: round $accent-darken-1; }
    FilterableSelect OptionList { height: auto; max-height: 6; border: thick $accent; display: none; margin-top: 0; padding: 0; background: $panel; border-top: none; width: 100%; }
    FilterableSelect OptionList:focus { border: thick $accent-darken-1; }
    FilterableSelect .visible { display: block; }
    """

    options: reactive[List[FilterableSelectOption]] = reactive([])
    filtered_options: reactive[List[FilterableSelectOption]] = reactive([])
    show_options: reactive[bool] = reactive(False)
    selected_id: reactive[Optional[int]] = reactive(None)
    selected_name: reactive[str] = reactive("")
    _option_list_needs_update = var(False)

    def __init__(self, prompt: str = "Filter...", id: Optional[str] = None):
        super().__init__(id=id)
        self.prompt = prompt
        input_id = f"{id}-input" if id else None
        options_id = f"{id}-options" if id else None
        self._input = Input(placeholder=prompt, id=input_id)
        self._option_list = OptionList(id=options_id)

    def compose(self) -> ComposeResult:
        yield self._input
        yield self._option_list

    def on_mount(self) -> None:
        self.watch(self._input, "value", self._filter_options)
        self.watch(self, "options", self._update_list_flag)
        self.watch(self, "filtered_options", self._update_option_list)
        self.watch(self, "show_options", self._toggle_option_list_display)

    def _update_list_flag(self) -> None:
        self._option_list_needs_update = True
        self._filter_options(self._input.value)

    def _filter_options(self, filter_value: str) -> None:
        filter_value = filter_value.lower()
        if not filter_value:
            self.filtered_options = self.options[:]
        else:
            self.filtered_options = [
                opt for opt in self.options if filter_value in opt.display.lower()
            ]
        try:
            input_focused = self._input.has_focus
        except Exception: input_focused = False
        self.show_options = input_focused and (bool(self.filtered_options) or (not filter_value and bool(self.options)))

    def _update_option_list(self) -> None:
        if not self.is_mounted or not hasattr(self, '_option_list'): return
        option_list = self._option_list
        option_list.clear_options()
        for opt in self.filtered_options:
             option_list.add_option(opt.display)
        if self.filtered_options:
             option_list.highlighted = 0

    def _toggle_option_list_display(self) -> None:
        if not self.is_mounted or not hasattr(self, '_option_list'): return
        self._option_list.set_class(self.show_options, "visible")

    def on_input_focused(self, event: events.Focus) -> None:
        if event.sender == self._input:
            self._filter_options(self._input.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input == self._input:
            current_text = event.value
            match = next((opt for opt in self.options if opt.display == current_text), None)
            if match:
                if self.selected_id != match.id:
                    self.selected_id = match.id
                    self.selected_name = match.display
            else:
                if self.selected_id is not None:
                    self.selected_id = None
                    self.selected_name = ""

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list == self._option_list:
            event.stop()
            selected_index = event.option_index
            if 0 <= selected_index < len(self.filtered_options):
                selected_option = self.filtered_options[selected_index]
                self.selected_id = selected_option.id
                self.selected_name = selected_option.display
                self._input.value = selected_option.display
                self._input.cursor_position = len(self._input.value)
                self.show_options = False
                self.post_message(ItemSelected(str(self.id), self.selected_id, self.selected_name))
                self.screen.set_focus(None)

    def on_key(self, event: events.Key) -> None:
        has_internal_focus = self.has_focus or self._input.has_focus or self._option_list.has_focus

        if has_internal_focus:
            option_list = self._option_list
            input_empty = not self._input.value

            if event.key in ("down", "up") and input_empty and not self.show_options:
                 event.stop()
                 self.filtered_options = self.options[:]
                 self.show_options = True
                 self._option_list.focus()
                 if event.key == "down": self._option_list.action_first()
                 else: self._option_list.action_last()
                 return

            if self.show_options and self.filtered_options:
                if event.key == "down":
                    event.stop()
                    option_list.action_cursor_down()
                    if self._input.has_focus: self._option_list.focus()
                elif event.key == "up":
                    event.stop()
                    option_list.action_cursor_up()
                    if self._input.has_focus: self._option_list.focus()
                elif event.key == "tab":
                    event.stop()
                    highlighted_index = option_list.highlighted
                    if highlighted_index is not None and 0 <= highlighted_index < len(self.filtered_options):
                        selected_option = self.filtered_options[highlighted_index]
                        self._input.value = selected_option.display
                        self._input.cursor_position = len(self._input.value)
                        self._input.focus()
                        self.show_options = False
                elif event.key == "enter": # Keep focus on input after enter
                    event.stop()
                    highlighted_index = option_list.highlighted
                    if highlighted_index is not None and 0 <= highlighted_index < len(self.filtered_options):
                        selected_option = self.filtered_options[highlighted_index]
                        self.selected_id = selected_option.id
                        self.selected_name = selected_option.display
                        self._input.value = selected_option.display
                        self._input.cursor_position = len(self._input.value)
                        self.show_options = False
                        self.post_message(ItemSelected(str(self.id), self.selected_id, self.selected_name))
                        self._input.focus() # Keep focus on input

            if event.key == "escape":
                 if self.show_options:
                      event.stop()
                      self.show_options = False
                      self.screen.set_focus(None)

    def clear(self) -> None:
        if hasattr(self, '_input') and self._input.is_mounted:
            self._input.value = ""
        self.selected_id = None
        self.selected_name = ""
        self.filtered_options = []
        self.show_options = False

    def set_options(self, new_options: List[FilterableSelectOption]):
        self.options = [opt if isinstance(opt, FilterableSelectOption) else FilterableSelectOption(str(opt[0]), opt[1]) for opt in new_options]
        input_value = ""
        if hasattr(self, '_input') and self._input.is_mounted:
             input_value = self._input.value
        self._filter_options(input_value)

    def set_value_by_id(self, item_id: Optional[int]):
        if item_id is None:
            self.clear()
            return
        match = next((opt for opt in self.options if opt.id == item_id), None)
        if match:
            self.selected_id = match.id
            self.selected_name = match.display
            if hasattr(self, '_input') and self._input.is_mounted:
                 self._input.value = match.display
            self.show_options = False
        else:
            # Don't clear if match not found, options might still be loading
            logging.warning(f"ID {item_id} not found in current options for {self.id}. Options might be loading.")
            # self.clear()


# --- Confirmation Modal ---
class ConfirmDeleteModal(ModalScreen[bool]):
    """Modal to confirm deletion."""

    def __init__(self, item_description: str, name: str | None = None, id: str | None = None, classes: str | None = None):
        super().__init__(name=name, id=id, classes=classes)
        self.item_description = item_description

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(f"Delete '{self.item_description}'?", id="confirm-question")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", variant="error", id="confirm-yes")
                yield Button("No", variant="primary", id="confirm-no")

    def on_mount(self) -> None:
        self.query_one("#confirm-yes", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event: events.Key) -> None:
        if event.key in ("enter", "space") and self.query_one("#confirm-yes").has_focus:
             event.stop()
             self.dismiss(True)
        elif event.key == "escape":
             event.stop()
             self.dismiss(False)


# --- Main Application Screen ---
class MainAppScreen(Screen):
    """Main screen combining logging and reporting."""

    BINDINGS = [
        Binding("ctrl+s", "save_log", "Save / Update Log", show=True),
        Binding("escape", "reset_focus_or_cancel_edit", "Reset Focus / Cancel Edit", show=True),
        Binding("up", "adjust_time(-1)", "Adjust Time Up", show=True),
        Binding("down", "adjust_time(1)", "Adjust Time Down", show=True),
        Binding("f1", "change_date(-1)", "Prev Day", show=True),
        Binding("f2", "change_date(1)", "Next Day", show=True),
        Binding("f3", "change_date(0)", "Today", show=True),
        Binding("ctrl+o", "focus_overview", "Focus Overview", show=True),
        Binding("ctrl+d", "delete_log", "Delete Log Entry", show=True),
    ]

    selected_project_id: reactive[Optional[int]] = reactive(None)
    selected_stage_id: reactive[Optional[int]] = reactive(None)
    selected_focus_id: reactive[Optional[int]] = reactive(None)
    current_start_time: reactive[Optional[datetime.datetime]] = reactive(None)
    current_end_time: reactive[Optional[datetime.datetime]] = reactive(None)
    selected_date: reactive[datetime.date] = reactive(datetime.date.today)
    editing_log_id: reactive[Optional[int]] = reactive(None)
    _log_entry_being_edited: reactive[Optional[Dict]] = reactive(None)
    # <<< Store last selected RowKey from the event >>>
    _last_selected_row_key: reactive[Optional[RowKey]] = reactive(None)

    _projects: List[Dict] = []
    _stages: List[Dict] = []
    _focuses: List[Dict] = []
    _daily_logs: List[Dict] = []

    @staticmethod
    def _create_select_options(data: List[Dict], name_col: str = 'name', id_col: str = 'id') -> List[Tuple[str, Optional[int]]]:
        options = []
        if data:
            options = [(f"{row.get(name_col, 'N/A')} (ID: {row.get(id_col, 'N/A')})", row.get(id_col)) for row in data]
        return options

    @staticmethod
    def _create_stage_select_options(data: List[Dict]) -> List[Tuple[str, int]]:
        options = []
        if data:
            options = [(f"{row.get('project_name','?')} / {row.get('name','?')} (ID: {row.get('id','?')})", row.get('id'))
                       for row in data if row.get('id') is not None]
        return options

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Static(f"Date: {self.selected_date.isoformat()} (F1/F2/F3)", id="date-display")
        with Container(id="daily-overview-container"):
            yield Label("Daily Overview (Ctrl+O to focus)", id="daily-overview-title")
            yield DataTable(id="daily-log-table", cursor_type="row", zebra_stripes=True)
        with Container(id="log-container"):
            yield Label("Log Time", classes="title", id="log-form-title")
            yield Label("Project:", classes="label")
            yield FilterableSelect(prompt="Filter Project...", id="fselect-project")
            yield Label("Stage:", classes="label")
            yield FilterableSelect(prompt="Filter Stage...", id="fselect-stage")
            yield Label("Focus:", classes="label")
            yield FilterableSelect(prompt="Filter Focus...", id="fselect-focus")
            yield Label("Start Time:", classes="label")
            yield Input("", id="input-start-time", placeholder="HH:MM", validators=[DateTimeValidator()])
            yield Label("End Time:", classes="label")
            yield Input("", id="input-end-time", placeholder="HH:MM", validators=[DateTimeValidator()])
            yield Static("Ctrl+S Save/Update. Ctrl+O Overview. Ctrl+D Delete.", classes="instructions", id="log-instructions")

    def on_mount(self) -> None:
        self.load_projects()
        self.load_focuses()
        self.load_daily_logs()
        self.call_later(self.reset_log_form)

    @work(thread=True)
    def load_projects(self):
        self._projects = db.get_projects()
        project_options = [FilterableSelectOption(f"{p.get('name','?')} (ID: {p.get('id','?')})", p.get('id')) for p in self._projects]
        if self.is_mounted and self.query("#fselect-project"):
            self.app.call_from_thread(self.query_one("#fselect-project", FilterableSelect).set_options, project_options)

    @work(thread=True)
    def load_stages(self, project_id: Optional[int]):
        logging.debug(f"Worker: Loading stages for project_id: {project_id}")
        if project_id is None:
            self._stages = []
            stage_options = []
        else:
            self._stages = db.get_stages(project_id=project_id)
            stage_options = [FilterableSelectOption(f"{s.get('name','?')} (ID: {s.get('id','?')})", s.get('id')) for s in self._stages]

        if self.is_mounted and self.query("#fselect-stage"):
            # <<< Pass log entry data to update function >>>
            self.app.call_from_thread(self._update_stage_options, stage_options)

    def _update_stage_options(self, stage_options):
        """Update stage options and select the correct one if editing."""
        try:
            stage_select = self.query_one("#fselect-stage", FilterableSelect)
            stage_select.set_options(stage_options)
            logging.debug(f"Updated stage options. Edit mode: {self.editing_log_id is not None}")
            # If we are in edit mode, try to set the value based on stored log data
            if self.editing_log_id is not None and self._log_entry_being_edited:
                 stage_id_to_select = self._log_entry_being_edited.get('stage_id')
                 logging.debug(f"Attempting to set stage value for edit: {stage_id_to_select}")
                 stage_select.set_value_by_id(stage_id_to_select)
                 # <<< Set reactive var AFTER setting widget value >>>
                 self.selected_stage_id = stage_id_to_select
                 # <<< Call focus setting AFTER stage is set >>>
                 self._set_focus_value_for_edit(self._log_entry_being_edited.get('focus_id'))
            # else: # Don't clear automatically if not editing
                 # if self.selected_stage_id is not None:
                 #      stage_select.clear()
                 #      self.selected_stage_id = None
        except Exception as e:
            logging.exception("Error updating stage options")
            self.notify(f"Error updating stage options: {e}", severity="error")


    @work(thread=True)
    def load_focuses(self):
        self._focuses = db.get_focuses()
        focus_options = [FilterableSelectOption(f"{f.get('name','?')} (ID: {f.get('id','?')})", f.get('id')) for f in self._focuses]
        focus_options.insert(0, FilterableSelectOption("-- None --", None))

        if self.is_mounted and self.query("#fselect-focus"):
            # <<< Don't try to pre-select here, wait for edit mode logic >>>
            self.app.call_from_thread(self._update_focus_select, focus_options)

    def _update_focus_select(self, options):
        """Update focus options only."""
        try:
            focus_select = self.query_one("#fselect-focus", FilterableSelect)
            focus_select.set_options(options)
            logging.debug(f"Updated focus options.")
            # <<< Value setting moved to _set_focus_value_for_edit >>>
        except Exception as e:
            logging.exception("Error updating focus select")
            self.notify(f"Error updating focus select: {e}", severity="error")

    @work(thread=True)
    def load_daily_logs(self):
        self._daily_logs = db.get_log_entries_for_day(self.selected_date.isoformat())
        if self.is_mounted and self.query("#daily-log-table"):
            self.app.call_from_thread(self._update_daily_log_table, self._daily_logs)

    def _update_daily_log_table(self, log_data: List[Dict]):
        try:
            date_display = self.query_one("#date-display", Static)
            date_display.update(f"Date: {self.selected_date.isoformat()} (F1/F2/F3)")

            title = self.query_one("#daily-overview-title", Label)
            title.update("Daily Overview (Ctrl+O to focus)")
            table = self.query_one("#daily-log-table", DataTable)
            current_cursor = table.cursor_coordinate
            table.clear(columns=True)

            if not log_data:
                table.add_column("Status")
                table.add_row("No logs found for this day.")
                return

            cols = ["ID", "Start", "End", "Project", "Stage", "Focus"]
            table.add_columns(*cols)
            for row in log_data:
                start_time = utils.parse_datetime_string(row.get('start'))
                end_time = utils.parse_datetime_string(row.get('end'))
                # <<< Use simple string key >>>
                table.add_row(
                    str(row.get('id', '')),
                    start_time.strftime('%H:%M') if start_time else '??:??',
                    end_time.strftime('%H:%M') if end_time else '??:??',
                    row.get('project_name', '?'),
                    row.get('stage_name', '?'),
                    row.get('focus_name') or '',
                    key=str(row.get('id')) # Use simple string ID as the key
                )
            if 0 <= current_cursor.row < table.row_count:
                 table.move_cursor(row=current_cursor.row, column=current_cursor.column, animate=False)
            elif table.row_count > 0:
                 table.move_cursor(row=0, column=0, animate=False)

        except Exception as e:
            logging.exception("Error updating daily log table")
            self.notify(f"Error updating daily log table: {e}", severity="error")

    def watch_selected_date(self, old_date: datetime.date, new_date: datetime.date) -> None:
        self.load_daily_logs()
        self.reset_log_form()

    def watch_selected_project_id(self, old_id: Optional[int], new_id: Optional[int]) -> None:
        if old_id != new_id:
             logging.debug(f"Project ID changed from {old_id} to {new_id}. Loading stages.")
             self.load_stages(new_id)
             # Clear stage selection when project changes *unless* we are editing
             if not self.editing_log_id:
                  self.call_later(self._clear_filterable_select, "#fselect-stage")
                  self.selected_stage_id = None


    def watch_editing_log_id(self, old_id: Optional[int], new_id: Optional[int]) -> None:
        self.call_later(self._update_edit_mode_ui, new_id)

    def _update_edit_mode_ui(self, editing_id: Optional[int]) -> None:
        try:
            log_container = self.query_one("#log-container")
            log_title = self.query_one("#log-form-title", Label)
            is_editing = editing_id is not None
            log_container.set_class(is_editing, "editing")
            log_title.update(f"Editing Log ID: {editing_id}" if is_editing else "Log Time")
            logging.debug(f"Updated edit mode UI. Editing ID: {editing_id}")
        except Exception as e:
            logging.warning(f"Error updating edit mode UI (might be timing related): {e}")

    def action_change_date(self, direction: int) -> None:
        if direction == 0:
            self.selected_date = datetime.date.today()
        else:
            delta = datetime.timedelta(days=direction)
            self.selected_date += delta
        self.cancel_edit()

    def action_reset_focus_or_cancel_edit(self) -> None:
        if self.editing_log_id is not None:
            self.cancel_edit()
        elif isinstance(self.focused, (Input, Select, FilterableSelect, DataTable)):
            self.screen.set_focus(None)

    def action_save_log(self) -> None:
        self.save_log_entry()

    def action_adjust_time(self, direction: int) -> None:
        focused_widget = self.focused
        if isinstance(focused_widget, Input) and (focused_widget.id in ["input-start-time", "input-end-time"]):
            current_time_str = focused_widget.value
            try:
                validator = DateTimeValidator()
                if not validator.validate(current_time_str).is_valid and current_time_str:
                     self.app.bell()
                     return
                current_dt = datetime.datetime.combine(self.selected_date, datetime.datetime.strptime(current_time_str, "%H:%M").time())
            except ValueError:
                current_dt = self.current_start_time if focused_widget.id == "input-start-time" else self.current_end_time
                if not current_dt or current_dt.date() != self.selected_date:
                     current_dt = datetime.datetime.combine(self.selected_date, datetime.time(datetime.datetime.now().hour, 0))
                     current_dt = utils.snap_time_to_interval(current_dt)

            delta = datetime.timedelta(minutes=TIME_INCREMENT_MINUTES * -direction)
            new_dt = current_dt + delta

            if new_dt.date() != self.selected_date:
                 new_dt = datetime.datetime.combine(self.selected_date, new_dt.time())

            new_value = new_dt.strftime("%H:%M")
            focused_widget.value = new_value
            self.post_message(Input.Changed(focused_widget, value=new_value))
            focused_widget.cursor_position = len(focused_widget.value)
        else:
            self.app.bell()

    def action_focus_overview(self) -> None:
        try:
            table = self.query_one("#daily-log-table")
            if table.row_count > 0:
                 table.focus()
                 if table.cursor_coordinate.row < 0:
                      table.cursor_coordinate = Coordinate(row=0, column=0)
            else:
                 self.notify("No logs in overview to focus.", severity="warning")
        except Exception as e:
            self.notify(f"Could not focus overview table: {e}", severity="error")

    def action_delete_log(self) -> None:
        table = self.query_one("#daily-log-table")
        if not table.has_focus:
             self.notify("Focus the overview table (Ctrl+O) and select a row to delete.", severity="warning")
             return

        # <<< Use the stored key from the last selection event >>>
        row_key = self._last_selected_row_key
        if row_key is None or row_key.value is None:
            self.notify("No row selected or invalid key stored.", severity="warning")
            logging.warning(f"Delete attempted with invalid stored key: {row_key!r}")
            return

        key_value_str = str(row_key.value)
        logging.debug(f"Attempting delete. Stored RowKey Value: '{key_value_str}', Type: {type(key_value_str)}")

        try:
            log_id_to_delete = int(key_value_str)
            logging.debug(f"Converted ID for delete: {log_id_to_delete}")

            log_entry = next((log for log in self._daily_logs if log.get('id') == log_id_to_delete), None)
            description = f"Log ID {log_id_to_delete}"
            if log_entry:
                 start = utils.parse_datetime_string(log_entry.get('start'))
                 description += f" ({start.strftime('%H:%M') if start else '??:??'} - {log_entry.get('stage_name', '?')})"

            def check_confirm(confirmed: bool):
                if confirmed:
                    self.delete_log_entry_worker(log_id_to_delete)

            self.app.push_screen(ConfirmDeleteModal(item_description=description), check_confirm)

        except (ValueError, TypeError) as e:
             logging.error(f"Error converting key value '{key_value_str}' to int: {e}", exc_info=True)
             self.notify(f"Invalid log ID format in row key: '{key_value_str}'", title="Delete Error", severity="error")
        except Exception as e:
             logging.exception(f"Other error processing deletion. Key Value: '{key_value_str}', Error: {e}")
             self.notify(f"Error processing deletion for key '{key_value_str}': {e}", title="Delete Error", severity="error")


    @work(exclusive=True, thread=True)
    def delete_log_entry_worker(self, log_id: int) -> None:
        success = db.delete_log_entry(log_id)
        if success:
            self.app.call_from_thread(self.app.notify, f"Log entry {log_id} deleted.", severity="information")
            self.app.call_from_thread(self.load_daily_logs)
            if self.editing_log_id == log_id:
                 self.app.call_from_thread(self.cancel_edit)
        else:
            self.app.call_from_thread(self.app.notify, f"Failed to delete log entry {log_id}.", severity="error")

    def on_item_selected(self, message: ItemSelected) -> None:
        if not self.query(f"#{message.control_id}"): return

        if message.control_id == "fselect-project":
            self.selected_project_id = message.item_id
            try: self.query_one("#fselect-stage").focus()
            except Exception: pass
        elif message.control_id == "fselect-stage":
            self.selected_stage_id = message.item_id
            try: self.query_one("#fselect-focus").focus()
            except Exception: pass
        elif message.control_id == "fselect-focus":
             self.selected_focus_id = message.item_id
             #try: self.query_one("#input-start-time").focus() # No auto-focus
             #except Exception: pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "input-start-time":
            validator = DateTimeValidator()
            validation_result = validator.validate(event.value)
            event.input.set_class(not validation_result.is_valid and event.value != "", "input--invalid")
            if validation_result.is_valid:
                try:
                    time_obj = datetime.datetime.strptime(event.value, "%H:%M").time()
                    self.current_start_time = datetime.datetime.combine(self.selected_date, time_obj)
                except ValueError: self.current_start_time = None
            else: self.current_start_time = None
        elif event.input.id == "input-end-time":
            validator = DateTimeValidator()
            validation_result = validator.validate(event.value)
            event.input.set_class(not validation_result.is_valid and event.value != "", "input--invalid")
            if validation_result.is_valid:
                try:
                    time_obj = datetime.datetime.strptime(event.value, "%H:%M").time()
                    self.current_end_time = datetime.datetime.combine(self.selected_date, time_obj)
                except ValueError: self.current_end_time = None
            else: self.current_end_time = None


    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "fselect-project-input" and self.query("#fselect-stage"):
            self.query_one("#fselect-stage").focus()
        elif event.input.id == "fselect-stage-input" and self.query("#fselect-focus"):
             self.query_one("#fselect-focus").focus()
        elif event.input.id == "fselect-focus-input" and self.query("#input-start-time"):
             self.query_one("#input-start-time").focus()
        elif event.input.id == "input-start-time" and self.query("#input-end-time"):
            self.query_one("#input-end-time").focus()
        elif event.input.id == "input-end-time":
            self.action_save_log()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = event.control
        if table.id == "daily-log-table":
            # <<< Store the RowKey from the event >>>
            self._last_selected_row_key = event.row_key
            logging.debug(f"Row Selected. Stored RowKey: {self._last_selected_row_key!r}")

            if self._last_selected_row_key and self._last_selected_row_key.value is not None:
                key_value_str = str(self._last_selected_row_key.value)
                logging.debug(f"Row Selected. Key Value Str: '{key_value_str}', Type: {type(key_value_str)}")
                try:
                    log_id = int(key_value_str)
                    logging.debug(f"Row Selected. Converted log_id: {log_id}")
                    selected_log = next((log for log in self._daily_logs if log.get('id') == log_id), None)
                    if selected_log:
                        logging.debug(f"Found log entry to edit: {selected_log}")
                        self.populate_form_for_edit(selected_log)
                    else:
                        logging.warning(f"Log ID {log_id} not found in self._daily_logs")
                        self.notify(f"Could not find data for log ID {log_id}", severity="error")
                except (ValueError, TypeError) as e:
                    logging.error(f"Error converting key value '{key_value_str}' to int: {e}", exc_info=True)
                    self.notify(f"Invalid log ID in table row key: '{key_value_str}'", title="Selection Error", severity="error")
            else:
                logging.warning(f"Row Selected, but row_key or row_key.value is None. RowKey: {self._last_selected_row_key!r}")
                self.notify("Could not get row key for selected row.", severity="warning")


    def populate_form_for_edit(self, log_entry: Dict):
        log_id = log_entry.get('id')
        if log_id is None:
             self.notify("Cannot edit log entry without an ID.", severity="error")
             return

        logging.debug(f"Populating form for edit. Log Entry: {log_entry}")
        self._log_entry_being_edited = log_entry # Store data for later use
        self.editing_log_id = log_id # Enter edit mode (watcher updates title)

        project_id = log_entry.get('project_id')
        stage_id = log_entry.get('stage_id') # Store target stage ID
        focus_id = log_entry.get('focus_id') # Store target focus ID

        logging.debug(f"Extracted IDs - Project: {project_id}, Stage: {stage_id}, Focus: {focus_id}")

        # Set Project value first
        try:
            project_select = self.query_one("#fselect-project", FilterableSelect)
            if not project_select.options:
                 logging.warning("Project options not loaded yet in populate_form_for_edit. Deferring.")
                 self.call_later(self.populate_form_for_edit, log_entry) # Retry whole population
                 return

            project_select.set_value_by_id(project_id)
            logging.debug(f"Set project widget value for ID: {project_id}")
            # Set reactive var *after* widget to trigger watcher correctly
            # Ensure watcher triggers even if ID is the same
            if self.selected_project_id == project_id:
                 self.load_stages(project_id) # Manually trigger stage load
            else:
                 self.selected_project_id = project_id

        except Exception as e:
            logging.exception(f"Error setting project select: {e}")
            self.notify(f"Error setting project: {e}", severity="error")

        # Set Focus value directly (no dependency)
        try:
            focus_widget = self.query_one("#fselect-focus", FilterableSelect)
            if not focus_widget.options:
                 logging.warning("Focus options not loaded yet in populate_form_for_edit. Retrying.")
                 # Retry setting focus value later, after options likely loaded
                 self.call_later(lambda: self._set_focus_value_for_edit(focus_id), delay=0.1)
            else:
                 self._set_focus_value_for_edit(focus_id)
        except Exception as e:
            logging.exception(f"Error setting focus widget: {e}")
            self.notify(f"Error setting focus: {e}", severity="error")

        # Stage value setting is handled by _update_stage_options callback

        start_dt = utils.parse_datetime_string(log_entry.get('start'))
        end_dt = utils.parse_datetime_string(log_entry.get('end'))
        logging.debug(f"Parsed Times - Start: {start_dt}, End: {end_dt}")
        self.current_start_time = start_dt
        self.current_end_time = end_dt


    def _set_focus_value_for_edit(self, focus_id: Optional[int]):
         """Helper to set focus value, ensuring options are loaded."""
         try:
              focus_widget = self.query_one("#fselect-focus", FilterableSelect)
              if not focus_widget.options:
                   logging.warning("Focus options still not loaded in _set_focus_value_for_edit. Retrying.")
                   self.call_later(self._set_focus_value_for_edit, focus_id) # Retry
                   return
              focus_widget.set_value_by_id(focus_id)
              self.selected_focus_id = focus_id
              logging.debug(f"Set focus widget value for ID: {focus_id}")
         except Exception as e:
             logging.exception(f"Error setting focus widget in helper: {e}")
             self.notify(f"Error setting focus: {e}", severity="error")


    # Removed _set_stage_focus_for_edit

    def cancel_edit(self):
        if self.editing_log_id is not None:
            logging.debug("Cancelling edit.")
            self.editing_log_id = None
            self._log_entry_being_edited = None
            self.reset_log_form()
            self.notify("Edit cancelled.", severity="information")

    def reset_log_form(self):
        try:
            logging.debug("Resetting log form.")
            self.call_later(self._clear_filterable_select, "#fselect-project")
            self.call_later(self._clear_filterable_select, "#fselect-stage")
            self.call_later(self._clear_filterable_select, "#fselect-focus")
            self.selected_project_id = None
            self.selected_stage_id = None
            self.selected_focus_id = None
            self.editing_log_id = None
            self._log_entry_being_edited = None
            self.reset_log_form_times()
        except Exception as e:
            logging.exception(f"Error during reset_log_form: {e}")

    def _clear_filterable_select(self, selector: str):
         try:
              widget = self.query_one(selector, FilterableSelect)
              widget.clear()
              logging.debug(f"Cleared widget {selector}")
         except Exception as e:
             logging.warning(f"Error clearing widget {selector}: {e}")


    def reset_log_form_times(self):
        if self.editing_log_id is None:
             logging.debug("Resetting times (scheduling fetch).")
             self.set_timer(0.01, self.fetch_last_entry_and_reset_times)

    @work(thread=True)
    def fetch_last_entry_and_reset_times(self):
        if self.editing_log_id is None:
            logging.debug("Worker fetching last entry for time reset.")
            daily_logs = db.get_log_entries_for_day(self.selected_date.isoformat())
            last_entry_today = daily_logs[-1] if daily_logs else None
            if self.is_mounted:
                 self.app.call_from_thread(self._apply_time_reset, last_entry_today)

    def _apply_time_reset(self, last_entry_today: Optional[Dict]):
        if self.editing_log_id is None:
            logging.debug(f"Applying time reset based on last entry: {last_entry_today}")
            default_start = None
            if last_entry_today and last_entry_today.get('end'):
                parsed_last_end = utils.parse_datetime_string(last_entry_today['end'])
                if parsed_last_end and parsed_last_end.date() == self.selected_date:
                     default_start = parsed_last_end

            if default_start:
                 start_dt = default_start
            else:
                 start_dt = datetime.datetime.combine(self.selected_date, datetime.time(9, 0))
                 start_dt = utils.snap_time_to_interval(start_dt)

            end_dt = start_dt + datetime.timedelta(minutes=TIME_INCREMENT_MINUTES)

            logging.debug(f"Setting times - Start: {start_dt}, End: {end_dt}")
            self.current_start_time = start_dt
            self.current_end_time = end_dt

    def watch_current_start_time(self, time: Optional[datetime.datetime]):
        try: self.query_one("#input-start-time").value = time.strftime("%H:%M") if time else ""
        except: pass
    def watch_current_end_time(self, time: Optional[datetime.datetime]):
        try: self.query_one("#input-end-time").value = time.strftime("%H:%M") if time else ""
        except: pass

    @work(exclusive=True, thread=True)
    def save_log_entry(self) -> None:
        start_dt = self.current_start_time
        end_dt = self.current_end_time
        stage_id = self.query_one("#fselect-stage", FilterableSelect).selected_id
        focus_id = self.query_one("#fselect-focus", FilterableSelect).selected_id
        log_id_to_update = self.editing_log_id

        errors = []
        start_input = self.query_one("#input-start-time", Input)
        end_input = self.query_one("#input-end-time", Input)

        if stage_id is None: errors.append("Stage must be selected.")
        start_validator = DateTimeValidator()
        end_validator = DateTimeValidator()
        if not start_validator.validate(start_input.value).is_valid: errors.append("Valid start time (HH:MM) required.")
        if not end_validator.validate(end_input.value).is_valid: errors.append("Valid end time (HH:MM) required.")
        if not start_dt: errors.append("Start time parsing failed.")
        if not end_dt: errors.append("End time parsing failed.")
        if start_dt and end_dt and end_dt <= start_dt: errors.append("End time must be after start time.")

        if errors:
            error_message = "Cannot Save Log:\n" + "\n".join(errors)
            self.app.call_from_thread(self.app.notify, message=error_message, title="Validation Error", severity="error", timeout=5)
            return

        start_str = utils.format_datetime_string(start_dt)
        end_str = utils.format_datetime_string(end_dt)

        success = False
        action = "saved"
        db_func_args = {
            "stage_id": stage_id,
            "focus_id": focus_id,
            "start_time": start_str,
            "end_time": end_str
        }

        try:
            if log_id_to_update is not None:
                action = "updated"
                db_func_args["log_id"] = log_id_to_update
                success = db.update_log_entry(**db_func_args)
            else:
                action = "added"
                success = db.add_log_entry(**db_func_args)

            if success:
                self.app.call_from_thread(self.app.notify, f"Log entry {action}!", title="Success", severity="information", timeout=3)
                self.app.call_from_thread(self.load_daily_logs)
                self.app.call_from_thread(self.reset_log_form)
                self.app.call_from_thread(lambda: self.query_one("#fselect-project").focus())
            else:
                self.app.call_from_thread(self.app.notify, f"Database error {action.replace('ed','ing')} log.", title="DB Error", severity="error", timeout=5)

        except Exception as e:
             logging.exception("Error saving log entry to database")
             self.app.call_from_thread(self.app.notify, f"An unexpected error occurred: {e}", title="Error", severity="error", timeout=5)
