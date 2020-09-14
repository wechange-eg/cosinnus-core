import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchConferenceError,
  setFetchConferenceSuccess,
  setFetchTranslationsError,
  setFetchTranslationsSuccess
} from "./actions"
import {ConferenceState} from "./reducer"

/**
 * Fetch conference data
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchConference: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: ConferenceState) => {
        dispatch(setFetchConferenceSuccess(data))
      })
    } else {
      dispatch(setFetchConferenceError("Failed to fetch translations"))
    }
  })
