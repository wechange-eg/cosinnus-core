import { createSlice } from "@reduxjs/toolkit";

export interface MessageState {
  text?: string
}

const messageSlice = createSlice({
  name: "message",
  initialState: {} as MessageState,
  reducers: {
    setMessage: (state, action) => {
      return { text: action.payload.non_field_errors[0] };
    },
    clearMessage: () => {
      return { text: "" };
    },
  }
})

export const {setMessage, clearMessage} = messageSlice.actions;
export default messageSlice.reducer;