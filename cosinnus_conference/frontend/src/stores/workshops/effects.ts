import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchWorkshopsError,
  setFetchWorkshopsSuccess
} from "./actions"
import {groupBySlots} from "../../utils/events"
import {EventJson} from "../events/models"

/**
 * Fetch conference workshops
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchWorkshops: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/workshops/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: EventJson[]) => {
        dispatch(setFetchWorkshopsSuccess(groupBySlots(data)))
      })
    } else {
      dispatch(setFetchWorkshopsError("Failed to fetch workshops"))
    }
  })
