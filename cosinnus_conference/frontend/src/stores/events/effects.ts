import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchEventsError, setFetchEventsLoading,
  setFetchEventsSuccess
} from "./actions"
import {EventJson, Event} from "./models"
import {RootState} from "../rootReducer"

/**
 * Fetch conference events
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchEvents: ReduxThunkActionCreator<[boolean], Promise<void>> = (fetchAll) => (
  dispatch: Dispatch, getState: () => RootState) => {
  const state = getState()
  const roomId = state.room && state.room.props.id.toString() || "0"
  dispatch(setFetchEventsLoading(roomId))
  let filterParam = ""
  if (!fetchAll) {
    filterParam = "room_id=" + roomId
  }
  return fetch(`/api/v2/conferences/${window.conferenceId}/events/?page_size=1000&limit=1000&${filterParam}`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: {results: EventJson[]}) => {
        dispatch(setFetchEventsSuccess(roomId, data.results.map(json => Event.fromJson(json))))
      })
    } else {
      dispatch(setFetchEventsError(roomId, "Failed to fetch events"))
    }
  })
}
