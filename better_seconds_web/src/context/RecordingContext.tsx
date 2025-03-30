import React, { createContext, useContext, useEffect, useState } from 'react'

interface RecordingContextProps {
  isRecording: boolean;
  setIsRecording: (value: boolean) => void;
}

const RecordingContext = createContext<RecordingContextProps | undefined>(undefined);

export const RecordingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isRecording, setIsRecordingState] = useState<boolean>(() => {
    // Carrega o estado inicial do Local Storage
    const storedValue = localStorage.getItem("isRecording");
    return storedValue ? JSON.parse(storedValue) : false;
  });

  // Função para atualizar o estado e salvar no Local Storage
  const setIsRecording = (value: boolean) => {
    setIsRecordingState(value);
    localStorage.setItem("isRecording", JSON.stringify(value));
  };


  return (
    <RecordingContext.Provider value={{ isRecording, setIsRecording }}>
      {children}
    </RecordingContext.Provider>
  );
};

export const useRecording = (): RecordingContextProps => {
  const context = useContext(RecordingContext);
  if (!context) {
    throw new Error("useRecording must be used within a RecordingProvider");
  }
  return context;
};