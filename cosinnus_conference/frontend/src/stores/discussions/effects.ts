import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchDiscussionsError,
  setFetchDiscussionsSuccess
} from "./actions"
import {groupBySlots} from "../../utils/events"
import {EventJson} from "../events/models"

/**
 * Fetch conference discussions
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchDiscussions: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/discussions/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: EventJson[]) => {
        dispatch(setFetchDiscussionsSuccess(groupBySlots(data)))
      })
    } else {
      dispatch(setFetchDiscussionsError("Failed to fetch discussions"))
    }
  })
