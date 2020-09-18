import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchEventsError,
  setFetchEventsSuccess
} from "./actions"
import {EventJson} from "./models"
import {groupBySlots} from "../../utils/events"

/**
 * Fetch conference room (events and Rocket.Chat URL)
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchEvents: ReduxThunkActionCreator<[string],
  Promise<void>> = (room: string) => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/${room}/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: EventJson[]) => {
        dispatch(setFetchEventsSuccess(room, groupBySlots(data)))
      })
    } else {
      dispatch(setFetchEventsError(room, "Failed to fetch events"))
    }
  })
