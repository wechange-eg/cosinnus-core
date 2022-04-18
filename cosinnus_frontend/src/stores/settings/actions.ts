import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Settings} from "./models"

export const setFetchSettingsSuccess: ReduxActionCreator<Settings> = conference => ({
  type: ActionType.FETCH_SETTINGS_SUCCESS,
  payload: conference
})

export const setFetchSettingsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_SETTINGS_ERROR,
  payload: Error(errorMessage),
  error: true
})