import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchConferenceError,
  setFetchConferenceSuccess,
} from "./actions"
import {setRoom} from "../room/actions"
import {Conference, ConferenceJson} from "./models"
import {Room} from "../room/models"

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
      response.json().then((data: ConferenceJson) => {
        dispatch(setFetchConferenceSuccess(Conference.fromJson(data)))
        dispatch(setRoom(Room.fromJson(data.rooms.find(room => room.id === window.conferenceRoomId))))
      })
    } else {
      dispatch(setFetchConferenceError("Failed to fetch translations"))
    }
  })
