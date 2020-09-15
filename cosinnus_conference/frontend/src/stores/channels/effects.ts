import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchChannelsError,
  setFetchChannelsSuccess
} from "./actions"
import {Channel} from "./reducer"

/**
 * Fetch conference channels
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchChannels: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/channels/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: Channel[]) => {
        dispatch(setFetchChannelsSuccess(data))
      })
    } else {
      dispatch(setFetchChannelsError("Failed to fetch channels"))
    }
  })
