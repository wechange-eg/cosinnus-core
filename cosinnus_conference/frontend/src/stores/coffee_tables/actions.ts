import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Event} from "../events/models"

export const setFetchCoffeeTablesSuccess: ReduxActionCreator<Event[]> = coffee_tables => ({
  type: ActionType.FETCH_COFFEE_TABLES_SUCCESS,
  payload: coffee_tables
})

export const setFetchCoffeeTablesError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_COFFEE_TABLES_ERROR,
  payload: Error(errorMessage),
  error: true
})
