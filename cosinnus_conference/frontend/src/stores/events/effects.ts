import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchEventsError,
  setFetchEventsSuccess
} from "./actions"
import {EventJson} from "./models"
import {groupBySlots} from "../../utils/events"

/**
 * Fetch conference events
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchEvents: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/events/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: EventJson[]) => {
        dispatch(setFetchEventsSuccess(groupBySlots(data)))
      })
    } else {
      dispatch(setFetchEventsError("Failed to fetch events"))
    }
  })
