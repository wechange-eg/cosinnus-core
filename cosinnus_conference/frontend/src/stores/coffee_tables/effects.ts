import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchCoffeeTablesError,
  setFetchCoffeeTablesSuccess
} from "./actions"
import {EventJson, Event} from "../events/models"

/**
 * Fetch conference coffee tables
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchCoffeeTables: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/coffee-tables/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: EventJson[]) => {
        dispatch(setFetchCoffeeTablesSuccess(data.map((json) => Event.fromJson(json))))
      })
    } else {
      dispatch(setFetchCoffeeTablesError("Failed to fetch coffee tables"))
    }
  })
