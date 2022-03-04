import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchSettingsError,
  setFetchSettingsSuccess,
} from "./actions"
import {Settings, SettingsJson} from "./models"

/**
 * Fetch conference data
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchSettings: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`${process.env.API_URL}/settings/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: SettingsJson) => {
        dispatch(setFetchSettingsSuccess(Settings.fromJson(data)))
      })
    } else {
      dispatch(setFetchSettingsError("Failed to fetch translations"))
    }
  })
