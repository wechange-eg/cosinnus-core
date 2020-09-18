import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchEventsError,
  setFetchEventsSuccess
} from "./actions"
import {EventJson} from "./models"
import {groupBySlots} from "../../utils/events"
import {RootState} from "../rootReducer"

/**
 * Fetch conference room (events and Rocket.Chat URL)
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchEvents: ReduxThunkActionCreator<[boolean], Promise<void>> = (fetchAll) => (dispatch: Dispatch, getState: () => RootState) => {
  const state = getState()
  const roomId = state.room && state.room.props.id || 0
  let filterParam = ""
  if (fetchAll && state.conference) {
    filterParam = "conference_id=" + state.conference.props.id
  } else {
    filterParam = "room_id=" + roomId
  }
  return fetch(`/api/v2/conference_events/?page_size=100&${filterParam}`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: {results: EventJson[]}) => {
        dispatch(setFetchEventsSuccess(roomId, groupBySlots(data.results)))
      })
    } else {
      dispatch(setFetchEventsError(roomId, "Failed to fetch events"))
    }
  })
}
