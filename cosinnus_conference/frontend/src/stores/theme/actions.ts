import {ActionType} from "../../constants/actions"
import {ThemeState} from "./reducer"
import {ReduxActionCreator} from "../../utils/types"

export const setTheme: ReduxActionCreator<ThemeState> = (theme: ThemeState) => ({
  type: ActionType.SET_THEME,
  payload: theme
})
